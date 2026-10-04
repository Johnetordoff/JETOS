"""JETOS subinterpreter service topology.

The main interpreter is the OS-level supervisor. Capability and device work may
run in isolated subinterpreters inside the same process.  Python 3.14's
``concurrent.interpreters`` module is the first implementation of this model.
"""
from __future__ import annotations

from dataclasses import dataclass
import queue
from typing import Iterable, Mapping

try:
    from concurrent import interpreters
except ImportError:  # pragma: no cover - for bootstrap hosts older than 3.14
    interpreters = None  # type: ignore[assignment]


DEFAULT_CAPABILITY_SERVICES = (
    "display",
    "network",
    "wireless",
    "bluetooth",
    "storage",
    "audio",
    "input",
    "camera",
    "power",
    "virtualization",
    "serial",
)


@dataclass(frozen=True)
class ServicePlan:
    name: str
    capability: str
    evidence: tuple[str, ...] = ()


@dataclass
class ServiceHandle:
    plan: ServicePlan
    interpreter: object
    inbox: object
    outbox: object
    thread: object


def supported() -> bool:
    """Return whether this runtime exposes the Python 3.14 interpreter API."""
    return bool(
        interpreters is not None
        and getattr(__import__("sys").implementation, "supports_isolated_interpreters", False)
    )


def plan_services(
    snapshot: Mapping[str, object],
    *,
    per_device: bool = False,
) -> tuple[ServicePlan, ...]:
    """Convert a capability snapshot into an interpreter service plan.

    The default is one service interpreter per present capability.  ``per_device``
    expands useful evidence entries into one interpreter per discovered device.
    It is intentionally optional because interpreter-per-device is not always the
    cheapest or best ownership boundary.
    """
    capabilities = snapshot.get("capabilities", {})
    if not isinstance(capabilities, Mapping):
        return ()

    plans: list[ServicePlan] = []
    for capability in DEFAULT_CAPABILITY_SERVICES:
        raw = capabilities.get(capability)
        if not isinstance(raw, Mapping) or not raw.get("present"):
            continue
        evidence_raw = raw.get("evidence", ())
        evidence = tuple(
            str(item)
            for item in evidence_raw
            if isinstance(item, (str, int, float))
        ) if isinstance(evidence_raw, Iterable) and not isinstance(evidence_raw, (str, bytes)) else ()

        if per_device and evidence:
            useful = tuple(item for item in evidence if not item.startswith("active:"))
            if useful:
                for index, item in enumerate(useful):
                    plans.append(
                        ServicePlan(
                            name=f"{capability}:{index}",
                            capability=capability,
                            evidence=(item,),
                        )
                    )
                continue

        plans.append(
            ServicePlan(
                name=capability,
                capability=capability,
                evidence=evidence,
            )
        )

    return tuple(plans)


def _service_loop(
    service_name: str,
    capability: str,
    evidence: tuple[str, ...],
    inbox: object,
    outbox: object,
) -> None:
    """Minimal actor loop executed inside a subinterpreter."""
    inbox_queue = inbox
    outbox_queue = outbox
    outbox_queue.put(("ready", service_name, capability, evidence))  # type: ignore[attr-defined]
    while True:
        message = inbox_queue.get()  # type: ignore[attr-defined]
        if message == ("stop",):
            outbox_queue.put(("stopped", service_name))  # type: ignore[attr-defined]
            return
        if message == ("ping",):
            outbox_queue.put(("pong", service_name, capability))  # type: ignore[attr-defined]
            continue
        outbox_queue.put(("echo", service_name, message))  # type: ignore[attr-defined]


class InterpreterSupervisor:
    """Own long-lived service subinterpreters from the main JETOS interpreter."""

    def __init__(self) -> None:
        if not supported():
            raise RuntimeError(
                "JETOS service interpreters require Python/JETOS Language 3.14+ "
                "with isolated interpreter support"
            )
        assert interpreters is not None
        self.main_id = interpreters.get_main().id
        self._services: dict[str, ServiceHandle] = {}

    @property
    def services(self) -> tuple[str, ...]:
        return tuple(sorted(self._services))

    def start(self, plan: ServicePlan, *, timeout: float = 5.0) -> ServiceHandle:
        if plan.name in self._services:
            return self._services[plan.name]
        assert interpreters is not None
        interpreter = interpreters.create()
        inbox = interpreters.create_queue()
        outbox = interpreters.create_queue()
        thread = interpreter.call_in_thread(
            _service_loop,
            plan.name,
            plan.capability,
            plan.evidence,
            inbox,
            outbox,
        )
        ready = outbox.get(timeout=timeout)
        if ready[:1] != ("ready",):
            raise RuntimeError(f"unexpected service startup response: {ready!r}")
        handle = ServiceHandle(plan, interpreter, inbox, outbox, thread)
        self._services[plan.name] = handle
        return handle

    def start_plans(self, plans: Iterable[ServicePlan]) -> tuple[ServiceHandle, ...]:
        return tuple(self.start(plan) for plan in plans)

    def request(
        self,
        name: str,
        message: tuple[object, ...],
        *,
        timeout: float = 5.0,
    ) -> object:
        handle = self._services[name]
        handle.inbox.put(message)  # type: ignore[attr-defined]
        return handle.outbox.get(timeout=timeout)  # type: ignore[attr-defined]

    def close(self, name: str, *, timeout: float = 5.0) -> None:
        handle = self._services.pop(name)
        handle.inbox.put(("stop",))  # type: ignore[attr-defined]
        response = handle.outbox.get(timeout=timeout)  # type: ignore[attr-defined]
        if response[:1] != ("stopped",):
            raise RuntimeError(f"unexpected service shutdown response: {response!r}")
        handle.thread.join(timeout=timeout)  # type: ignore[attr-defined]
        handle.interpreter.close()  # type: ignore[attr-defined]

    def close_all(self) -> None:
        for name in tuple(self._services):
            self.close(name)

    def __enter__(self) -> "InterpreterSupervisor":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close_all()
