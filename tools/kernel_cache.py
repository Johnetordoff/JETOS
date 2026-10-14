#!/usr/bin/env python3
"""Correctness-preserving cache for fully built JetOS kernel images."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = ROOT / ".jetos-cache" / "kernel"
CACHE_VERSION = 2


def run(args: list[str], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_git_head(source: Path) -> str | None:
    try:
        head = run(["git", "-C", str(source), "rev-parse", "HEAD"], capture=True).stdout.strip()
        status = run(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"], capture=True).stdout
    except subprocess.CalledProcessError:
        return None
    if status.strip():
        return None
    return head


def executable_identity(executable: str) -> dict[str, object]:
    resolved = shutil.which(executable)
    if not resolved:
        return {"command": executable, "missing": True}
    version = "unknown"
    for flag in ("--version", "-v"):
        proc = subprocess.run(
            [resolved, flag],
            text=True,
            capture_output=True,
            check=False,
        )
        text = (proc.stdout + proc.stderr).strip()
        if text:
            version = text
            break
    path = Path(resolved)
    stat = path.stat()
    return {
        "command": executable,
        "resolved": str(path.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path.resolve()),
        "version": version,
    }


def command_identity(command: str) -> list[dict[str, object]]:
    identities: list[dict[str, object]] = []
    for token in shlex.split(command):
        if token.startswith("-") or "=" in token:
            continue
        resolved = shutil.which(token)
        if resolved:
            identities.append(executable_identity(token))
    if not identities:
        identities.append({"command": command, "missing": True})
    return identities


def fingerprint(source: Path, arch: str) -> tuple[str, dict[str, object]] | None:
    head = clean_git_head(source)
    if head is None:
        return None

    build_script = ROOT / "tools" / "build.py"
    dockerfile = ROOT / "Dockerfile"
    relevant_env = {
        name: os.environ.get(name, "")
        for name in (
            "CC",
            "HOSTCC",
            "CROSS_COMPILE",
            "LLVM",
            "LLVM_IAS",
            "KCFLAGS",
            "KCPPFLAGS",
            "KAFLAGS",
            "LDFLAGS",
            "KBUILD_BUILD_TIMESTAMP",
            "KBUILD_BUILD_USER",
            "KBUILD_BUILD_HOST",
        )
    }
    payload: dict[str, object] = {
        "cache_version": CACHE_VERSION,
        "linux_head": head,
        "arch": arch,
        "build_py_sha256": sha256_file(build_script),
        "dockerfile_sha256": sha256_file(dockerfile),
        "environment": relevant_env,
        "cc_identity": command_identity(os.environ.get("CC", "cc")),
        "hostcc_identity": command_identity(os.environ.get("HOSTCC", os.environ.get("CC", "cc"))),
        "tool_identities": {
            name: executable_identity(name)
            for name in ("ld", "as", "ar", "objcopy", "make", "bison", "flex", "perl", "python3")
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    key = hashlib.sha256(encoded).hexdigest()
    return key, payload


def kernel_image(build_source: Path, arch: str) -> Path:
    return build_source / ("arch/x86/boot/bzImage" if arch == "x86_64" else "arch/arm64/boot/Image")


def try_restore(cache_dir: Path, image: Path) -> bool:
    cached_image = cache_dir / "kernel-image"
    metadata_path = cache_dir / "metadata.json"
    if not cached_image.is_file() or not metadata_path.is_file():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    expected = metadata.get("image_sha256")
    if not isinstance(expected, str) or sha256_file(cached_image) != expected:
        return False
    image.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cached_image, image)
    if sha256_file(image) != expected:
        image.unlink(missing_ok=True)
        return False
    print(f"JETOS kernel cache: HIT {cache_dir.name}", flush=True)
    return True


def store(cache_dir: Path, image: Path, payload: dict[str, object]) -> None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kernel-cache-", dir=CACHE_ROOT) as temporary:
        temp = Path(temporary)
        staged_image = temp / "kernel-image"
        shutil.copy2(image, staged_image)
        metadata = {
            "fingerprint": payload,
            "image_sha256": sha256_file(staged_image),
        }
        (temp / "metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        os.replace(temp, cache_dir)
        Path(temporary).mkdir(exist_ok=True)
    print(f"JETOS kernel cache: STORED {cache_dir.name}", flush=True)


def build_or_restore(build_source: Path, source: Path, arch: str) -> Path:
    image = kernel_image(build_source, arch)
    calculated = fingerprint(source, arch)
    if calculated is not None:
        key, payload = calculated
        cache_dir = CACHE_ROOT / key
        if try_restore(cache_dir, image):
            return image
    else:
        key = ""
        payload = {}
        cache_dir = Path()
        print("JETOS kernel cache: disabled because source/linux is not a clean recorded Git tree", flush=True)

    run([sys.executable, "tools/build.py", "kernel", str(build_source), "--arch", arch])
    if not image.is_file():
        raise SystemExit(f"kernel build did not produce {image}")

    if calculated is not None:
        store(cache_dir, image, payload)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or restore a verified JetOS kernel image")
    parser.add_argument("build_source")
    parser.add_argument("--source", required=True)
    parser.add_argument("--arch", required=True, choices=("x86_64", "arm64"))
    args = parser.parse_args()
    build_or_restore(Path(args.build_source), Path(args.source), args.arch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
