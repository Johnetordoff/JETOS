"""JETOS reference desktop shell.

Tkinter renders the first desktop, while layout and application selection are
owned by JETOS. The Start menu is generated from hardware capabilities that
Linux exposes through the JETOS hardware registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import argparse
import code
import contextlib
import io
import os
import pprint
import re
from typing import Callable

from jetos import apps, hardware

try:
    import tkinter as tk
except ImportError:  # pragma: no cover - exercised on hosts without Tk
    tk = None  # type: ignore[assignment]


MIN_WIDTH = 1
MIN_HEIGHT = 1


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True)
class DesktopLayout:
    screen: Rect
    taskbar: Rect
    start_button: Rect
    clock: Rect
    welcome_window: Rect
    scale: float


def parse_geometry(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*", value)
    if not match:
        raise ValueError(f"invalid geometry {value!r}; expected WIDTHxHEIGHT")
    width, height = (int(part) for part in match.groups())
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        raise ValueError("display dimensions must be positive")
    return width, height


def _clamp(value: int, minimum: int, maximum: int) -> int:
    if maximum < minimum:
        return maximum
    return max(minimum, min(value, maximum))


def layout_for(width: int, height: int) -> DesktopLayout:
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        raise ValueError("display dimensions must be positive")

    # 640x480 is a visual reference, never a required display mode.
    scale = max(0.25, min(width / 640.0, height / 480.0))

    taskbar_height = _clamp(round(30 * scale), 1, height)
    taskbar = Rect(0, height - taskbar_height, width, taskbar_height)

    margin = _clamp(round(3 * scale), 0, max(0, taskbar_height // 3))
    content_height = max(1, taskbar_height - 2 * margin)

    start_width = _clamp(round(56 * scale), 1, max(1, width))
    start_button = Rect(
        margin,
        taskbar.y + margin,
        min(start_width, max(1, width - margin)),
        min(content_height, taskbar_height),
    )

    clock_width = _clamp(round(72 * scale), 1, max(1, width))
    clock_x = max(0, width - clock_width - margin)
    clock = Rect(
        clock_x,
        taskbar.y + margin,
        min(clock_width, width - clock_x),
        min(content_height, taskbar_height),
    )

    work_height = max(0, taskbar.y)
    preferred_w = round(360 * scale)
    preferred_h = round(180 * scale)
    window_w = _clamp(preferred_w, 1, max(1, width))
    window_h = _clamp(preferred_h, 1, max(1, work_height or height))
    welcome_window = Rect(
        max(0, (width - window_w) // 2),
        max(0, ((work_height or height) - window_h) // 2),
        window_w,
        window_h,
    )

    return DesktopLayout(
        screen=Rect(0, 0, width, height),
        taskbar=taskbar,
        start_button=start_button,
        clock=clock,
        welcome_window=welcome_window,
        scale=scale,
    )


def _font_size(scale: float, base: int, minimum: int = 5) -> int:
    return max(minimum, round(base * scale))


class Desktop:
    """Tk renderer for the JETOS desktop layout and capability applications."""

    def __init__(
        self,
        width: int | None = None,
        height: int | None = None,
        *,
        fullscreen: bool = False,
        splash_ms: int = 850,
        now: Callable[[], datetime] = datetime.now,
        machine_snapshot: dict[str, object] | None = None,
    ) -> None:
        if tk is None:
            raise RuntimeError("tkinter is unavailable in this JETOS Language runtime")

        self.root = tk.Tk()
        self.root.title("JETOS")
        self.root.configure(bg="#008080")
        self.root.resizable(True, True)
        self.now = now
        self.splash_ms = max(0, splash_ms)
        self.machine_snapshot = machine_snapshot or hardware.discover()
        self.app_specs = apps.available(self.machine_snapshot)
        self._app_by_title = {app.title: app for app in self.app_specs}
        self._clock_item: int | None = None
        self._fullscreen = fullscreen
        self._last_layout: DesktopLayout | None = None

        if fullscreen:
            self.root.attributes("-fullscreen", True)
            self.root.update_idletasks()
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
        else:
            width = width or min(960, self.root.winfo_screenwidth())
            height = height or min(720, self.root.winfo_screenheight())
            self.root.geometry(f"{width}x{height}+40+40")

        self.width = max(1, int(width))
        self.height = max(1, int(height))

        self.canvas = tk.Canvas(
            self.root,
            highlightthickness=0,
            bd=0,
            bg="#008080",
        )
        self.canvas.pack(fill="both", expand=True)

        self.start_menu = tk.Menu(
            self.root,
            tearoff=False,
            bg="#c0c0c0",
            fg="#000000",
            activebackground="#000080",
            activeforeground="#ffffff",
        )
        for app in self.app_specs:
            self.start_menu.add_command(
                label=app.title,
                command=lambda selected=app: self._launch(selected),
            )

        self.root.bind("<Configure>", self._on_configure)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.canvas.tag_bind("start", "<Button-1>", self._show_start_menu)

        self._show_splash()
        self.root.after(1000, self._refresh_clock)

    def _toggle_fullscreen(self, _event: object) -> None:
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)

    def _on_configure(self, event: object) -> None:
        width = getattr(event, "width", self.width)
        height = getattr(event, "height", self.height)
        if width <= 1 or height <= 1:
            return
        self.width = width
        self.height = height
        if self.splash_ms == 0:
            self._draw_desktop()

    def _show_splash(self) -> None:
        self.canvas.delete("all")
        self.canvas.configure(bg="#000000")
        cx = self.width // 2
        cy = self.height // 2
        scale = layout_for(self.width, self.height).scale
        self.canvas.create_text(
            cx,
            cy - _font_size(scale, 14),
            text="JETOS",
            fill="#ffffff",
            font=("TkDefaultFont", _font_size(scale, 28), "bold"),
        )
        self.canvas.create_text(
            cx,
            cy + _font_size(scale, 20),
            text="Starting JETOS Language…",
            fill="#c0c0c0",
            font=("TkDefaultFont", _font_size(scale, 10)),
        )
        self.root.after(self.splash_ms, self._finish_splash)

    def _finish_splash(self) -> None:
        self.splash_ms = 0
        self._draw_desktop()

    def _bevel(
        self,
        rect: Rect,
        *,
        fill: str = "#c0c0c0",
        sunken: bool = False,
        tags: tuple[str, ...] = (),
    ) -> None:
        self.canvas.create_rectangle(
            rect.x,
            rect.y,
            rect.right - 1,
            rect.bottom - 1,
            fill=fill,
            outline=fill,
            tags=tags,
        )
        bright = "#ffffff"
        shadow = "#808080"
        dark = "#000000"
        top = shadow if sunken else bright
        left = shadow if sunken else bright
        bottom = bright if sunken else dark
        right = bright if sunken else dark
        self.canvas.create_line(rect.x, rect.y, rect.right - 1, rect.y, fill=top, tags=tags)
        self.canvas.create_line(rect.x, rect.y, rect.x, rect.bottom - 1, fill=left, tags=tags)
        self.canvas.create_line(
            rect.x,
            rect.bottom - 1,
            rect.right - 1,
            rect.bottom - 1,
            fill=bottom,
            tags=tags,
        )
        self.canvas.create_line(
            rect.right - 1,
            rect.y,
            rect.right - 1,
            rect.bottom - 1,
            fill=right,
            tags=tags,
        )

    def _draw_background(self, layout: DesktopLayout) -> None:
        self.canvas.configure(bg="#008080")
        self.canvas.create_rectangle(
            0,
            0,
            layout.screen.width,
            layout.taskbar.y,
            fill="#008080",
            outline="#008080",
        )
        spacing = max(12, round(40 * layout.scale))
        limit = layout.screen.width + max(0, layout.taskbar.y)
        for offset in range(-layout.taskbar.y, limit, spacing):
            self.canvas.create_line(
                offset,
                0,
                offset - layout.taskbar.y,
                layout.taskbar.y,
                fill="#007878",
            )

    def _clock_text(self) -> str:
        if os.name == "nt":
            return self.now().strftime("%I:%M %p").lstrip("0")
        return self.now().strftime("%-I:%M %p")

    def _draw_taskbar(self, layout: DesktopLayout) -> None:
        self._bevel(layout.taskbar)
        self._bevel(layout.start_button, tags=("start",))
        self.canvas.create_text(
            layout.start_button.x + layout.start_button.width // 2,
            layout.start_button.y + layout.start_button.height // 2,
            text="Start",
            font=("TkDefaultFont", _font_size(layout.scale, 9), "bold"),
            fill="#000000",
            tags=("start",),
        )

        self._bevel(layout.clock, sunken=True)
        self._clock_item = self.canvas.create_text(
            layout.clock.x + layout.clock.width // 2,
            layout.clock.y + layout.clock.height // 2,
            text=self._clock_text(),
            font=("TkDefaultFont", _font_size(layout.scale, 8)),
            fill="#000000",
        )

    def _draw_welcome(self, layout: DesktopLayout) -> None:
        rect = layout.welcome_window
        self._bevel(rect)
        title_height = _clamp(round(22 * layout.scale), 1, rect.height)
        title = Rect(rect.x + 3, rect.y + 3, max(1, rect.width - 6), title_height)
        self.canvas.create_rectangle(
            title.x,
            title.y,
            title.right,
            title.bottom,
            fill="#000080",
            outline="#000080",
        )
        self.canvas.create_text(
            title.x + max(3, round(5 * layout.scale)),
            title.y + title.height // 2,
            anchor="w",
            text="JETOS",
            fill="#ffffff",
            font=("TkDefaultFont", _font_size(layout.scale, 9), "bold"),
        )
        self.canvas.create_text(
            rect.x + rect.width // 2,
            rect.y + max(title_height + 8, rect.height // 2 - _font_size(layout.scale, 8)),
            text="Welcome to JETOS",
            fill="#000000",
            font=("TkDefaultFont", _font_size(layout.scale, 12)),
        )
        self.canvas.create_text(
            rect.x + rect.width // 2,
            rect.y + max(title_height + 8, rect.height // 2 + _font_size(layout.scale, 12)),
            text=f"{len(self.app_specs)} applications from detected capabilities",
            fill="#000000",
            font=("TkDefaultFont", _font_size(layout.scale, 8)),
        )

    def _draw_desktop(self) -> None:
        self.canvas.delete("all")
        layout = layout_for(self.width, self.height)
        self._last_layout = layout
        self._draw_background(layout)
        self._draw_welcome(layout)
        self._draw_taskbar(layout)

    def _refresh_clock(self) -> None:
        try:
            exists = self.root.winfo_exists()
        except Exception:
            return
        if not exists:
            return
        if self.splash_ms == 0 and self._clock_item is not None:
            self.canvas.itemconfigure(self._clock_item, text=self._clock_text())
        self.root.after(1000, self._refresh_clock)

    def _show_start_menu(self, event: object) -> None:
        self.start_menu.update_idletasks()
        x_root = int(getattr(event, "x_root", self.root.winfo_rootx()))
        y_root = int(getattr(event, "y_root", self.root.winfo_rooty()))
        height = self.start_menu.winfo_reqheight()
        try:
            self.start_menu.tk_popup(x_root, max(self.root.winfo_rooty(), y_root - height))
        finally:
            self.start_menu.grab_release()

    def _window(self, title: str, width: int = 440, height: int = 300):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.configure(bg="#c0c0c0")
        window.geometry(f"{width}x{height}")
        return window

    def _launch(self, app: apps.AppSpec) -> None:
        if app.key == "terminal":
            self._open_terminal()
        elif app.key == "system":
            self._open_system()
        else:
            self._open_capability(app)

    def _open_terminal(self) -> None:
        window = self._window("JETOS Terminal", 560, 360)
        transcript = tk.Text(
            window,
            bg="#000000",
            fg="#c0c0c0",
            insertbackground="#ffffff",
            font=("TkFixedFont", 10),
            wrap="word",
        )
        transcript.pack(fill="both", expand=True, padx=4, pady=(4, 0))
        entry = tk.Entry(window, font=("TkFixedFont", 10))
        entry.pack(fill="x", padx=4, pady=4)
        console = code.InteractiveConsole(
            {
                "hardware": hardware,
                "snapshot": self.machine_snapshot,
            }
        )
        state = {"prompt": "jetos> "}

        def append(text: str) -> None:
            transcript.insert("end", text)
            transcript.see("end")

        append("JETOS Language terminal\n")
        append("hardware and snapshot are preloaded.\n\n")

        def execute(_event: object | None = None) -> str:
            command = entry.get()
            entry.delete(0, "end")
            append(state["prompt"] + command + "\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                more = console.push(command)
            append(output.getvalue())
            state["prompt"] = ".....> " if more else "jetos> "
            return "break"

        entry.bind("<Return>", execute)
        entry.focus_set()

    def _open_system(self) -> None:
        window = self._window("JETOS System", 620, 420)
        text = tk.Text(window, bg="#ffffff", fg="#000000", font=("TkFixedFont", 9))
        text.pack(fill="both", expand=True, padx=4, pady=4)
        text.insert("1.0", pprint.pformat(self.machine_snapshot, width=88, sort_dicts=True))
        text.configure(state="disabled")

    def _open_capability(self, app: apps.AppSpec) -> None:
        details = apps.capability_details(app, self.machine_snapshot)
        window = self._window(f"JETOS {app.title}", 480, 260)
        present = bool(details.get("present"))
        active = bool(details.get("active"))
        evidence = details.get("evidence", ())
        lines = [
            f"Capability: {app.capability}",
            f"Present: {'yes' if present else 'no'}",
            f"Active: {'yes' if active else 'no'}",
            "",
            "Kernel evidence:",
        ]
        if isinstance(evidence, (tuple, list)) and evidence:
            lines.extend(f"  {item}" for item in evidence)
        else:
            lines.append("  none")
        label = tk.Label(
            window,
            text="\n".join(lines),
            justify="left",
            anchor="nw",
            bg="#c0c0c0",
            fg="#000000",
            font=("TkFixedFont", 9),
        )
        label.pack(fill="both", expand=True, padx=12, pady=12)

    def run(self) -> None:
        self.root.mainloop()


def run(
    geometry: tuple[int, int] | None = None,
    *,
    fullscreen: bool = False,
    splash_ms: int = 850,
    machine_snapshot: dict[str, object] | None = None,
) -> None:
    width = height = None
    if geometry is not None:
        width, height = geometry
    Desktop(
        width,
        height,
        fullscreen=fullscreen,
        splash_ms=splash_ms,
        machine_snapshot=machine_snapshot,
    ).run()


def main() -> int:
    parser = argparse.ArgumentParser(description="JETOS Tkinter desktop shell")
    parser.add_argument(
        "--geometry",
        help="preview geometry, for example 640x480 or 517x301",
    )
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--no-splash", action="store_true")
    args = parser.parse_args()

    geometry = parse_geometry(args.geometry) if args.geometry else None
    run(
        geometry,
        fullscreen=args.fullscreen,
        splash_ms=0 if args.no_splash else 850,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
