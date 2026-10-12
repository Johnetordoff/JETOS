#!/usr/bin/env python3
"""Qualify Python's interaction contract with the JETOS OS and filesystem.

Every probe runs in its own interpreter so process/session/signal/permission tests
cannot contaminate later checks.  The suite also inventories the callable
surface of Linux-facing standard-library modules.  Platform capabilities that
are not exposed by this Python build are recorded as SKIP; regressions are
caught by comparing manifests and by the CPython OS regression suite.
"""
from __future__ import annotations

import argparse
import asyncio
import filecmp
import fnmatch
import glob
import grp
import inspect
import json
import mmap
import os
from pathlib import Path
import pwd
import resource
import selectors
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Callable

SKIP = 77

OS_MODULES = (
    "os",
    "posix",
    "pathlib",
    "shutil",
    "tempfile",
    "stat",
    "glob",
    "fnmatch",
    "filecmp",
    "mmap",
    "fcntl",
    "resource",
    "pwd",
    "grp",
    "signal",
    "subprocess",
    "selectors",
    "select",
    "socket",
    "socketserver",
    "pty",
    "termios",
    "tty",
    "multiprocessing",
    "multiprocessing.shared_memory",
    "threading",
    "concurrent.futures",
    "asyncio",
    "time",
    "platform",
    "locale",
    "getpass",
    "syslog",
    "ctypes",
)

CPYTHON_OS_TESTS = (
    "test_os",
    "test_posix",
    "test_posixpath",
    "test_pathlib",
    "test_shutil",
    "test_tempfile",
    "test_stat",
    "test_filecmp",
    "test_glob",
    "test_fnmatch",
    "test_mmap",
    "test_fcntl",
    "test_resource",
    "test_pwd",
    "test_grp",
    "test_signal",
    "test_subprocess",
    "test_socket",
    "test_select",
    "test_selectors",
    "test_pty",
    "test_termios",
    "test_threading",
    "test_multiprocessing_fork",
    "test_asyncio",
    "test_time",
    "test_syslog",
)


def skip(reason: str) -> None:
    print(f"SKIP: {reason}")
    raise SystemExit(SKIP)


def require(name: str) -> Any:
    value = getattr(os, name, None)
    if value is None:
        skip(f"os.{name} is not exposed by this build")
    return value


def probe_filesystem_basic() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path = root / "alpha"
        path.write_bytes(b"jetos")
        assert path.read_bytes() == b"jetos"
        with path.open("ab") as stream:
            stream.write(b"-python")
            stream.flush()
            os.fsync(stream.fileno())
        assert path.read_bytes() == b"jetos-python"
        path.truncate(5)
        assert path.read_bytes() == b"jetos"
        replacement = root / "replacement"
        replacement.write_text("new", encoding="utf-8")
        os.replace(replacement, path)
        assert path.read_text(encoding="utf-8") == "new"
        renamed = root / "renamed"
        os.rename(path, renamed)
        assert renamed.exists()
        os.unlink(renamed)
        assert not renamed.exists()


def probe_low_level_fd() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "fd")
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_TRUNC, 0o600)
        try:
            assert os.write(fd, b"abcdef") == 6
            os.lseek(fd, 0, os.SEEK_SET)
            assert os.read(fd, 3) == b"abc"
            os.ftruncate(fd, 4)
            os.fsync(fd)
            if hasattr(os, "fdatasync"):
                os.fdatasync(fd)
            info = os.fstat(fd)
            assert info.st_size == 4
            assert os.isatty(fd) is False
        finally:
            os.close(fd)


def probe_positioned_io() -> None:
    pread = require("pread")
    pwrite = require("pwrite")
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "pos")
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.write(fd, b"0123456789")
            assert pread(fd, 3, 4) == b"456"
            assert pwrite(fd, b"XYZ", 2) == 3
            assert pread(fd, 5, 0) == b"01XYZ"
        finally:
            os.close(fd)


def probe_vectored_io() -> None:
    readv = require("readv")
    writev = require("writev")
    rfd, wfd = os.pipe()
    try:
        assert writev(wfd, [b"jet", b"os"]) == 5
        a = bytearray(3)
        b = bytearray(2)
        assert readv(rfd, [a, b]) == 5
        assert bytes(a + b) == b"jetos"
    finally:
        os.close(rfd)
        os.close(wfd)


def probe_fd_dup_inherit() -> None:
    rfd, wfd = os.pipe()
    duplicate = os.dup(wfd)
    try:
        os.set_inheritable(duplicate, True)
        assert os.get_inheritable(duplicate)
        os.set_inheritable(duplicate, False)
        assert not os.get_inheritable(duplicate)
        os.write(duplicate, b"x")
        assert os.read(rfd, 1) == b"x"
    finally:
        os.close(duplicate)
        os.close(rfd)
        os.close(wfd)


def probe_pipe_flags() -> None:
    pipe2 = require("pipe2")
    rfd, wfd = pipe2(getattr(os, "O_CLOEXEC", 0))
    try:
        os.write(wfd, b"p")
        assert os.read(rfd, 1) == b"p"
    finally:
        os.close(rfd)
        os.close(wfd)


def probe_directories() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        nested = root / "a" / "b" / "c"
        nested.mkdir(parents=True)
        (nested / "x").write_text("x", encoding="utf-8")
        assert "a" in os.listdir(root)
        with os.scandir(nested) as it:
            entries = list(it)
        assert len(entries) == 1 and entries[0].is_file()
        walked = [Path(base) / name for base, _, names in os.walk(root) for name in names]
        assert walked and walked[0].name == "x"
        cwd = os.getcwd()
        os.chdir(nested)
        try:
            assert Path.cwd() == nested
            fd = os.open(root, os.O_RDONLY)
            try:
                if hasattr(os, "fchdir"):
                    os.fchdir(fd)
                    assert Path.cwd() == root
            finally:
                os.close(fd)
        finally:
            os.chdir(cwd)


def probe_links() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        original = root / "original"
        original.write_text("jetos", encoding="utf-8")
        hard = root / "hard"
        symbolic = root / "symbolic"
        os.link(original, hard)
        os.symlink(original.name, symbolic)
        assert os.stat(original).st_ino == os.stat(hard).st_ino
        assert os.readlink(symbolic) == original.name
        assert symbolic.read_text(encoding="utf-8") == "jetos"
        assert stat.S_ISLNK(os.lstat(symbolic).st_mode)


def probe_permissions() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "mode"
        path.write_text("x", encoding="utf-8")
        os.chmod(path, 0o640)
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o640
        fd = os.open(path, os.O_RDONLY)
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(fd, 0o600)
                assert stat.S_IMODE(os.fstat(fd).st_mode) == 0o600
        finally:
            os.close(fd)
        previous = os.umask(0o077)
        os.umask(previous)
        assert os.access(path, os.R_OK)
        uid = os.getuid()
        gid = os.getgid()
        if hasattr(os, "chown"):
            os.chown(path, uid, gid)
        if hasattr(os, "lchown"):
            link = Path(td) / "link"
            os.symlink(path.name, link)
            os.lchown(link, uid, gid)


def probe_metadata_times() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "time"
        path.write_text("x", encoding="utf-8")
        target_ns = 1_600_000_000_123_456_789
        os.utime(path, ns=(target_ns, target_ns))
        info = os.stat(path)
        assert abs(info.st_mtime_ns - target_ns) < 1_000_000_000
        vfs = os.statvfs(path)
        assert vfs.f_bsize > 0


def probe_extended_attributes() -> None:
    for name in ("setxattr", "getxattr", "listxattr", "removexattr"):
        require(name)
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "xattr"
        path.write_bytes(b"x")
        key = "user.jetos"
        try:
            os.setxattr(path, key, b"python")
            assert os.getxattr(path, key) == b"python"
            assert key in os.listxattr(path)
            os.removexattr(path, key)
        except OSError as exc:
            skip(f"filesystem does not support user xattrs: {exc}")


def probe_fifo() -> None:
    if not hasattr(os, "mkfifo"):
        skip("os.mkfifo unavailable")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "fifo"
        os.mkfifo(path, 0o600)
        assert stat.S_ISFIFO(os.stat(path).st_mode)
        rfd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        wfd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        try:
            os.write(wfd, b"f")
            assert os.read(rfd, 1) == b"f"
        finally:
            os.close(rfd)
            os.close(wfd)


def probe_copy_primitives() -> None:
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "src"
        dst = Path(td) / "dst"
        src.write_bytes(b"0123456789")
        sfd = os.open(src, os.O_RDONLY)
        dfd = os.open(dst, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            if hasattr(os, "copy_file_range"):
                copied = os.copy_file_range(sfd, dfd, 10)
                assert copied == 10
            elif hasattr(os, "sendfile"):
                copied = os.sendfile(dfd, sfd, 0, 10)
                assert copied == 10
            else:
                skip("copy_file_range/sendfile unavailable")
        finally:
            os.close(sfd)
            os.close(dfd)
        assert dst.read_bytes() == b"0123456789"


def probe_splice() -> None:
    splice = require("splice")
    r1, w1 = os.pipe()
    r2, w2 = os.pipe()
    try:
        os.write(w1, b"jetos")
        assert splice(r1, w2, 5) == 5
        assert os.read(r2, 5) == b"jetos"
    finally:
        for fd in (r1, w1, r2, w2):
            os.close(fd)


def probe_file_allocation_advice() -> None:
    fallocate = require("posix_fallocate")
    fadvise = require("posix_fadvise")
    with tempfile.TemporaryDirectory() as td:
        fd = os.open(Path(td) / "alloc", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fallocate(fd, 0, 4096)
            assert os.fstat(fd).st_size >= 4096
            fadvise(fd, 0, 4096, getattr(os, "POSIX_FADV_NORMAL", 0))
        finally:
            os.close(fd)


def probe_memfd() -> None:
    memfd_create = require("memfd_create")
    fd = memfd_create("jetos", getattr(os, "MFD_CLOEXEC", 0))
    try:
        os.write(fd, b"memory-file")
        os.lseek(fd, 0, os.SEEK_SET)
        assert os.read(fd, 11) == b"memory-file"
    finally:
        os.close(fd)


def probe_eventfd() -> None:
    eventfd = require("eventfd")
    read = require("eventfd_read")
    write = require("eventfd_write")
    fd = eventfd(0, getattr(os, "EFD_CLOEXEC", 0))
    try:
        write(fd, 7)
        assert read(fd) == 7
    finally:
        os.close(fd)


def probe_pidfd() -> None:
    pidfd_open = require("pidfd_open")
    fd = pidfd_open(os.getpid())
    try:
        assert fd >= 0
    finally:
        os.close(fd)


def probe_random() -> None:
    getrandom = require("getrandom")
    data = getrandom(32)
    assert isinstance(data, bytes) and len(data) == 32
    assert len(os.urandom(32)) == 32


def probe_process_fork_wait() -> None:
    if not hasattr(os, "fork"):
        skip("os.fork unavailable")
    pid = os.fork()
    if pid == 0:
        os._exit(23)
    waited, status_value = os.waitpid(pid, 0)
    assert waited == pid
    assert os.waitstatus_to_exitcode(status_value) == 23


def probe_exec() -> None:
    if not hasattr(os, "fork"):
        skip("fork unavailable")
    pid = os.fork()
    if pid == 0:
        os.execl(sys.executable, sys.executable, "-c", "raise SystemExit(17)")
    _, status_value = os.waitpid(pid, 0)
    assert os.waitstatus_to_exitcode(status_value) == 17


def probe_posix_spawn() -> None:
    spawn = require("posix_spawn")
    pid = spawn(
        sys.executable,
        [sys.executable, "-c", "raise SystemExit(19)"],
        os.environ.copy(),
    )
    _, status_value = os.waitpid(pid, 0)
    assert os.waitstatus_to_exitcode(status_value) == 19


def probe_subprocess() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getpid())"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert int(result.stdout.strip()) > 0


def probe_signal_delivery() -> None:
    received: list[int] = []
    old = signal.signal(signal.SIGUSR1, lambda signum, frame: received.append(signum))
    try:
        os.kill(os.getpid(), signal.SIGUSR1)
        for _ in range(100):
            if received:
                break
            time.sleep(0.001)
        assert received == [signal.SIGUSR1]
    finally:
        signal.signal(signal.SIGUSR1, old)


def probe_process_identity() -> None:
    assert os.getpid() > 0
    assert os.getppid() >= 0
    assert pwd.getpwuid(os.getuid()).pw_uid == os.getuid()
    assert grp.getgrgid(os.getgid()).gr_gid == os.getgid()
    assert isinstance(os.getgroups(), list)
    assert os.uname().sysname
    if hasattr(os, "getpgid"):
        assert os.getpgid(0) >= 0
    if hasattr(os, "getsid"):
        assert os.getsid(0) >= 0


def probe_environment() -> None:
    key = "JETOS_OS_QUALIFY"
    os.environ[key] = "python"
    assert os.getenv(key) == "python"
    os.putenv(key, "os")
    # os.putenv need not synchronize the mapping, so verify through a child.
    result = subprocess.run(
        [sys.executable, "-c", f"import os; assert os.getenv('{key}') == 'os'"],
        check=False,
    )
    assert result.returncode == 0
    os.unsetenv(key)
    os.environ.pop(key, None)


def probe_resource_limits() -> None:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    target = min(soft, 256) if soft != resource.RLIM_INFINITY else 256
    resource.setrlimit(resource.RLIMIT_NOFILE, (target, hard))
    assert resource.getrlimit(resource.RLIMIT_NOFILE)[0] == target
    usage = resource.getrusage(resource.RUSAGE_SELF)
    assert usage.ru_utime >= 0


def probe_scheduler_affinity_priority() -> None:
    if hasattr(os, "sched_getaffinity"):
        mask = os.sched_getaffinity(0)
        assert mask
        os.sched_setaffinity(0, mask)
    if hasattr(os, "getpriority"):
        os.getpriority(os.PRIO_PROCESS, 0)
    if hasattr(os, "sched_yield"):
        os.sched_yield()


def probe_clocks() -> None:
    assert time.time() > 0
    assert time.monotonic() >= 0
    assert time.perf_counter() >= 0
    assert time.process_time() >= 0
    times = os.times()
    assert times.elapsed >= 0
    if hasattr(time, "clock_gettime"):
        assert time.clock_gettime(time.CLOCK_MONOTONIC) >= 0


def probe_mmap_file_and_anonymous() -> None:
    anon = mmap.mmap(-1, 4096)
    try:
        anon[:5] = b"jetos"
        assert anon[:5] == b"jetos"
    finally:
        anon.close()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "mapped"
        path.write_bytes(b"\0" * 4096)
        with path.open("r+b") as stream:
            mapped = mmap.mmap(stream.fileno(), 4096)
            try:
                mapped[:6] = b"python"
                mapped.flush()
            finally:
                mapped.close()
        assert path.read_bytes()[:6] == b"python"


def probe_fcntl_locks() -> None:
    try:
        import fcntl
    except ImportError:
        skip("fcntl unavailable")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "lock"
        path.write_bytes(b"x")
        with path.open("r+b") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.lockf(stream.fileno(), fcntl.LOCK_UN)
            flags = fcntl.fcntl(stream.fileno(), fcntl.F_GETFD)
            fcntl.fcntl(stream.fileno(), fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)


def probe_pty_termios() -> None:
    try:
        import pty
        import termios
    except ImportError as exc:
        skip(str(exc))
    master, slave = pty.openpty()
    try:
        attrs = termios.tcgetattr(slave)
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
        os.write(master, b"z")
    finally:
        os.close(master)
        os.close(slave)


def probe_selectors_pipe() -> None:
    rfd, wfd = os.pipe()
    selector = selectors.DefaultSelector()
    try:
        selector.register(rfd, selectors.EVENT_READ)
        os.write(wfd, b"s")
        ready = selector.select(timeout=1)
        assert ready
        assert os.read(rfd, 1) == b"s"
    finally:
        selector.close()
        os.close(rfd)
        os.close(wfd)


def probe_select_poll_epoll() -> None:
    import select

    rfd, wfd = os.pipe()
    try:
        os.write(wfd, b"x")
        readable, _, _ = select.select([rfd], [], [], 1)
        assert rfd in readable
        if hasattr(select, "poll"):
            poller = select.poll()
            poller.register(rfd, select.POLLIN)
            assert poller.poll(1000)
        if hasattr(select, "epoll"):
            ep = select.epoll()
            try:
                ep.register(rfd, select.EPOLLIN)
                assert ep.poll(1)
            finally:
                ep.close()
        os.read(rfd, 1)
    finally:
        os.close(rfd)
        os.close(wfd)


def probe_unix_socket() -> None:
    if not hasattr(socket, "AF_UNIX"):
        skip("AF_UNIX unavailable")
    with tempfile.TemporaryDirectory() as td:
        address = os.path.join(td, "sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(address)
            server.listen(1)
            client.connect(address)
            accepted, _ = server.accept()
            try:
                client.sendall(b"unix")
                assert accepted.recv(4) == b"unix"
            finally:
                accepted.close()
        finally:
            client.close()
            server.close()


def probe_socketpair() -> None:
    left, right = socket.socketpair()
    try:
        left.sendall(b"pair")
        assert right.recv(4) == b"pair"
    finally:
        left.close()
        right.close()


def probe_loopback_network() -> None:
    assert socket.getaddrinfo("localhost", 0)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    client = socket.create_connection(server.getsockname(), timeout=2)
    accepted, _ = server.accept()
    try:
        client.sendall(b"tcp")
        assert accepted.recv(3) == b"tcp"
    finally:
        accepted.close()
        client.close()
        server.close()

    udp_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp_b.bind(("127.0.0.1", 0))
        udp_a.sendto(b"udp", udp_b.getsockname())
        assert udp_b.recvfrom(3)[0] == b"udp"
    finally:
        udp_a.close()
        udp_b.close()

    if socket.has_ipv6:
        ipv6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            ipv6.bind(("::1", 0))
        finally:
            ipv6.close()


def probe_fd_passing() -> None:
    if not hasattr(socket, "SCM_RIGHTS"):
        skip("SCM_RIGHTS unavailable")
    import array

    left, right = socket.socketpair()
    with tempfile.TemporaryDirectory() as td:
        fd = os.open(Path(td) / "fd", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fds = array.array("i", [fd])
            left.sendmsg([b"F"], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fds)])
            data, ancdata, _, _ = right.recvmsg(1, socket.CMSG_LEN(fds.itemsize))
            assert data == b"F" and ancdata
            received = array.array("i")
            received.frombytes(ancdata[0][2][: fds.itemsize])
            os.close(received[0])
        finally:
            os.close(fd)
            left.close()
            right.close()


def probe_shared_memory() -> None:
    try:
        from multiprocessing import shared_memory
    except ImportError as exc:
        skip(str(exc))
    block = shared_memory.SharedMemory(create=True, size=16)
    try:
        block.buf[:5] = b"jetos"
        second = shared_memory.SharedMemory(name=block.name)
        try:
            assert bytes(second.buf[:5]) == b"jetos"
        finally:
            second.close()
    finally:
        block.close()
        block.unlink()


def probe_threads() -> None:
    values: list[int] = []
    event = threading.Event()

    def worker() -> None:
        values.append(1)
        event.set()

    thread = threading.Thread(target=worker)
    thread.start()
    assert event.wait(2)
    thread.join()
    assert values == [1]


def probe_multiprocessing_fork() -> None:
    import multiprocessing

    if "fork" not in multiprocessing.get_all_start_methods():
        skip("fork multiprocessing unavailable")
    ctx = multiprocessing.get_context("fork")
    parent, child = ctx.Pipe()
    proc = ctx.Process(target=child.send, args=("jetos",))
    proc.start()
    try:
        assert parent.recv() == "jetos"
    finally:
        proc.join(5)
    assert proc.exitcode == 0


def probe_asyncio_os() -> None:
    async def check() -> None:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "print('jetos')",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        assert process.returncode == 0
        assert stdout.strip() == b"jetos"

    asyncio.run(check())


def probe_pathlib_shutil_tempfile() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "source"
        source.mkdir()
        (source / "a.txt").write_text("a", encoding="utf-8")
        (source / "b.bin").write_bytes(b"b")
        copied = root / "copied"
        shutil.copytree(source, copied)
        assert (copied / "a.txt").read_text(encoding="utf-8") == "a"
        shutil.copy2(copied / "a.txt", root / "single")
        moved = root / "moved"
        shutil.move(copied, moved)
        assert moved.is_dir()
        usage = shutil.disk_usage(root)
        assert usage.total > 0
        shutil.rmtree(moved)
        assert not moved.exists()


def probe_glob_fnmatch_filecmp() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        a = root / "alpha.py"
        b = root / "beta.txt"
        c = root / "copy.py"
        a.write_text("same", encoding="utf-8")
        b.write_text("other", encoding="utf-8")
        c.write_text("same", encoding="utf-8")
        assert str(a) in glob.glob(str(root / "*.py"))
        assert fnmatch.fnmatch(a.name, "*.py")
        assert filecmp.cmp(a, c, shallow=False)
        assert not filecmp.cmp(a, b, shallow=False)


def probe_sysconf_pathconf() -> None:
    if hasattr(os, "sysconf"):
        assert os.sysconf("SC_PAGESIZE") > 0
    if hasattr(os, "pathconf"):
        with tempfile.TemporaryDirectory() as td:
            assert os.pathconf(td, "PC_NAME_MAX") > 0
    if hasattr(os, "confstr") and "CS_PATH" in getattr(os, "confstr_names", {}):
        assert os.confstr("CS_PATH") is not None


def probe_proc_sys_dev() -> None:
    for path in ("/proc/self", "/proc/meminfo", "/sys/kernel", "/dev/null", "/dev/zero"):
        assert Path(path).exists(), path
    with open("/dev/null", "wb") as null:
        assert null.write(b"jetos") == 5
    with open("/dev/zero", "rb") as zero:
        assert zero.read(8) == b"\0" * 8
    with open("/dev/urandom", "rb") as random_source:
        assert len(random_source.read(16)) == 16


def probe_chroot() -> None:
    chroot = require("chroot")
    if os.geteuid() != 0:
        skip("chroot requires root")
    with tempfile.TemporaryDirectory() as td:
        chroot(td)
        os.chdir("/")
        assert os.getcwd() == "/"


PROBES: dict[str, Callable[[], None]] = {
    "filesystem-basic": probe_filesystem_basic,
    "fd-low-level": probe_low_level_fd,
    "fd-positioned-io": probe_positioned_io,
    "fd-vectored-io": probe_vectored_io,
    "fd-dup-inherit": probe_fd_dup_inherit,
    "pipe-flags": probe_pipe_flags,
    "directories": probe_directories,
    "links": probe_links,
    "permissions": probe_permissions,
    "metadata-times-statvfs": probe_metadata_times,
    "extended-attributes": probe_extended_attributes,
    "fifo": probe_fifo,
    "copy-primitives": probe_copy_primitives,
    "splice": probe_splice,
    "file-allocation-advice": probe_file_allocation_advice,
    "memfd": probe_memfd,
    "eventfd": probe_eventfd,
    "pidfd": probe_pidfd,
    "random": probe_random,
    "process-fork-wait": probe_process_fork_wait,
    "process-exec": probe_exec,
    "posix-spawn": probe_posix_spawn,
    "subprocess": probe_subprocess,
    "signals": probe_signal_delivery,
    "process-identity": probe_process_identity,
    "environment": probe_environment,
    "resource-limits": probe_resource_limits,
    "scheduler-affinity-priority": probe_scheduler_affinity_priority,
    "clocks": probe_clocks,
    "mmap": probe_mmap_file_and_anonymous,
    "fcntl-locks": probe_fcntl_locks,
    "pty-termios": probe_pty_termios,
    "selectors": probe_selectors_pipe,
    "select-poll-epoll": probe_select_poll_epoll,
    "unix-socket": probe_unix_socket,
    "socketpair": probe_socketpair,
    "loopback-network": probe_loopback_network,
    "fd-passing": probe_fd_passing,
    "shared-memory": probe_shared_memory,
    "threads": probe_threads,
    "multiprocessing-fork": probe_multiprocessing_fork,
    "asyncio-os": probe_asyncio_os,
    "pathlib-shutil-tempfile": probe_pathlib_shutil_tempfile,
    "glob-fnmatch-filecmp": probe_glob_fnmatch_filecmp,
    "sysconf-pathconf": probe_sysconf_pathconf,
    "proc-sys-dev": probe_proc_sys_dev,
    "chroot": probe_chroot,
}


def callable_surface(module_name: str) -> dict[str, Any]:
    import importlib

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # record exact platform/build gap
        return {"import": "FAIL", "detail": f"{type(exc).__name__}: {exc}", "callables": []}

    callables: list[dict[str, Any]] = []
    for name, value in sorted(vars(module).items()):
        if not callable(value):
            continue
        try:
            signature_text = str(inspect.signature(value))
        except (TypeError, ValueError):
            signature_text = None
        callables.append(
            {
                "name": name,
                "kind": "class" if inspect.isclass(value) else "callable",
                "signature": signature_text,
            }
        )
    return {"import": "PASS", "callables": callables}


def run_probe(name: str) -> tuple[str, str]:
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--probe", name],
        text=True,
        capture_output=True,
        timeout=30,
    )
    output = (result.stderr or result.stdout).strip().splitlines()
    detail = output[-1] if output else ""
    if result.returncode == 0:
        return "PASS", detail
    if result.returncode == SKIP:
        return "SKIP", detail
    return "FAIL", detail or f"exit {result.returncode}"


def run_cpython_os_tests() -> tuple[bool, str]:
    command = [sys.executable, "-I", "-m", "test", "-j1", *CPYTHON_OS_TESTS]
    result = subprocess.run(command, text=True)
    return result.returncode == 0, f"exit {result.returncode}"


def comparable(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "modules": manifest.get("modules", {}),
        "probes": manifest.get("probes", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Qualify Python interaction with the JETOS OS/filesystem"
    )
    parser.add_argument("--probe", choices=sorted(PROBES))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if args.probe:
        PROBES[args.probe]()
        return 0

    manifest: dict[str, Any] = {
        "implementation": sys.implementation.name,
        "python": sys.version,
        "platform": sys.platform,
        "modules": {name: callable_surface(name) for name in OS_MODULES},
        "probes": {},
    }
    failures: list[str] = []

    for module_name, entry in manifest["modules"].items():
        status = entry["import"]
        print(f"{status} os-module {module_name}: {len(entry.get('callables', []))} callables")
        if status != "PASS":
            failures.append(f"module {module_name}")

    for name in sorted(PROBES):
        status, detail = run_probe(name)
        manifest["probes"][name] = {"status": status, "detail": detail}
        suffix = f": {detail}" if detail else ""
        print(f"{status} os-capability {name}{suffix}")
        if status == "FAIL":
            failures.append(f"probe {name}")

    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        if comparable(baseline) != comparable(manifest):
            print("FAIL Python/OS contract differs from baseline")
            failures.append("OS baseline")
        else:
            print("PASS Python/OS contract matches baseline")

    if args.full:
        passed, detail = run_cpython_os_tests()
        manifest["cpython_os_regression_suite"] = "PASS" if passed else f"FAIL: {detail}"
        print(f"{'PASS' if passed else 'FAIL'} CPython OS regression suite: {detail}")
        if not passed:
            failures.append("CPython OS regression suite")

    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"OS manifest: {args.manifest}")

    passed = sum(value["status"] == "PASS" for value in manifest["probes"].values())
    skipped = sum(value["status"] == "SKIP" for value in manifest["probes"].values())
    print(
        "Python/OS qualification: "
        f"{passed}/{len(PROBES)} probes PASS; {skipped} SKIP; {len(failures)} failures"
    )
    return int(args.strict and bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
