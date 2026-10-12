# JETOS Python ↔ kernel co-design experiments

Status: **active experimental program**

JETOS controls both the Python 3.14 userspace and the Linux-backed Gen 2 kernel profile. That creates an optimization opportunity ordinary CPython cannot assume: when a Python standard-library operation is forced to translate one high-level intent into a long sequence of generic POSIX/Linux operations, JETOS may add a narrow kernel primitive whose semantics match the Python operation more directly.

This is **not** permission to make Python depend unconditionally on JETOS. Every experiment keeps the normal Python 3.14 behavior as its reference semantics and fallback. A kernel fast path is accepted only when it preserves those semantics and measurably improves performance, code complexity, race resistance, resource lifetime, or syscall count.

## Rules

1. Python 3.14 behavior is the contract. Skinny kernel reduction must not silently reduce it.
2. New JETOS kernel APIs stay narrow and reviewable; do not create a second general-purpose userspace framework.
3. A fast path must have a normal Linux fallback until the JETOS path is proven.
4. Measure before and after: wall time, syscall count where practical, context switches, allocations where practical, and lines/branches of CPython glue replaced.
5. Prefer handle-based/race-resistant APIs over pathname re-resolution.
6. Do not move arbitrary Python policy into the kernel.
7. `preexec_fn`-style arbitrary Python execution remains a fallback case rather than being forced into an atomic kernel primitive.

## Experiment 1 — `jet_spawn`: atomic Python process construction

**Primary stdlib:** `subprocess`, `os`, `multiprocessing`

### Current impedance mismatch

`subprocess.Popen` must choose between `posix_spawn()` and `_posixsubprocess.fork_exec()`. The fallback path must coordinate fork/vfork, an error-reporting pipe, file-descriptor remapping/closing, cwd, credentials, umask, signals, sessions/process groups, and finally exec. The child is temporarily created mainly to configure itself and exec another image.

### Proposed primitive

Conceptual interface:

```text
jet_spawn(spec) -> {pid, pidfd}
```

`spec` contains executable/argv/env, cwd, stdin/stdout/stderr and fd mapping, inherited-fd allowlist, uid/gid/groups, umask, signal reset/mask, session/process-group requests, and flags.

The kernel constructs the child state and execs atomically from the caller's point of view. Failure returns the real exec/setup errno directly; success returns both PID and pidfd.

### Expected wins

- remove the fork/vfork child-setup dance for ordinary `Popen`;
- remove the dedicated exec-error pipe;
- direct pidfd ownership from process creation;
- reduce descriptor-close/dup userspace loops;
- avoid post-fork Python/C complexity in multi-threaded processes;
- simpler and more race-resistant process lifetime handling.

### Fallback

Normal Python 3.14 `subprocess` path, especially for `preexec_fn` and any option not represented by the primitive.

### Acceptance test

Same observable `Popen` behavior on the protected JETOS subprocess suite; lower median spawn latency and fewer syscalls/context switches on HC1.

---

## Experiment 2 — `jet_copy`: one semantic file-copy operation

**Primary stdlib:** `shutil`

### Current impedance mismatch

`shutil.copyfile()` probes platform capabilities and selects among `fcopyfile`, `copy_file_range`, `sendfile`, a Windows readinto path, and a Python read/write loop. `copy2()` then performs separate metadata work. Python therefore implements a decision tree around multiple kernel interfaces and partial-failure modes.

### Proposed primitive

```text
jet_copy(src_handle/path, dst_handle/path, flags) -> copy_result
```

Flags describe data-only vs metadata-preserving copy, symlink behavior, sparse extent preservation, copy-on-write eligibility, xattr policy, overwrite policy, and durability requirements.

The filesystem/kernel selects clone/reflink, copy_file_range, in-kernel buffered copy, or an appropriate fallback while preserving one documented result contract.

### Expected wins

- one Python fast path instead of several platform-specific branches;
- fewer open/stat/copy/chmod/utime/xattr transitions for `copy2` semantics;
- preserve sparse/reflink information without Python understanding filesystem internals;
- clearer partial-failure semantics.

### Fallback

Unmodified `shutil.copyfile`, `copy`, and `copy2`.

### Acceptance test

Byte-identical content and required metadata across the JETOS filesystem matrix; lower copy latency and syscall count for small-file trees and large files.

---

## Experiment 3 — `jet_walk`: batched tree traversal with stable entry metadata

**Primary stdlib:** `os.walk`, `os.fwalk`, `pathlib`, `glob`

### Current impedance mismatch

`os.walk()` repeatedly calls `scandir()`, classifies each entry, constructs paths, and may later re-check symlink state after yielding because the caller can mutate the tree. Higher-level `pathlib` and glob operations add more path joins and metadata probes.

### Proposed primitive

```text
jet_walk(root_handle/path, flags, batch_size) -> batches of entries
```

Each entry carries relative path/name, type, inode/generation identity, minimal stat metadata requested by flags, and a directory handle/cookie suitable for safe continuation. The operation is batched rather than one syscall per metadata question.

### Expected wins

- fewer directory-read/stat/readlink transitions;
- much less Python path construction for large trees;
- optional race-resistant handle-relative traversal;
- a reusable substrate for `os.walk`, `pathlib.rglob`, `glob`, manifest generation, and JETOS file provenance scans.

### Fallback

`os.scandir`/`os.walk` and existing `pathlib` logic.

### Acceptance test

Identical traversal sets/order where order is specified; correct symlink/follow behavior; substantial reduction in syscalls on the full Linux-source tree.

---

## Experiment 4 — `jet_waitset`: Python-shaped completion/event port

**Primary stdlib:** `selectors`, `asyncio`, `signal`, `subprocess`

### Current impedance mismatch

`asyncio` builds on readiness selectors and also maintains a self-socket used to wake the loop from another thread. Processes, signals, timers, sockets, and file readiness have different integration mechanisms. The event loop turns these into one Python scheduling model in userspace.

### Proposed primitive

```text
jet_waitset_create() -> handle
jet_waitset_ctl(handle, operations[])
jet_waitset_wait(handle, deadline, max_events) -> completion[]
```

A completion can represent fd readiness, pidfd/process exit, timer expiry, signal delivery, explicit cross-thread wakeup, and eventually supported asynchronous I/O completions. Registration and event collection are batchable.

### Expected wins

- remove asyncio's socketpair self-wakeup on JETOS;
- unify process, timer, signal, and fd notification under one wait primitive;
- batch registrations/completions;
- reduce selector-specific glue and syscalls per loop tick;
- provide a future completion-oriented path without forcing all Python code onto io_uring semantics.

### Fallback

`selectors.DefaultSelector`, existing asyncio self-pipe/socketpair, normal signal and process mechanisms.

### Acceptance test

Pass asyncio/selectors/subprocess/signal tests; lower idle wake cost and lower event-dispatch syscall count under HC1 network workloads.

---

## Experiment 5 — `jet_memregion`: automatically scoped shared-memory handles

**Primary stdlib:** `multiprocessing.shared_memory`, `multiprocessing.resource_tracker`

### Current impedance mismatch

Named POSIX shared memory and semaphores can outlive the creating Python process, so CPython starts a separate resource-tracker process, communicates registrations over a pipe, handles fork inheritance, and cleans leaked objects at shutdown.

### Proposed primitive

```text
jet_memregion_create(size, flags) -> memregion_handle
jet_memregion_share(handle, target/process/rights) -> transferable handle
```

The kernel owns region lifetime by handle/reference count. Regions disappear automatically when no authorized handle remains unless explicitly promoted to persistent lifetime.

### Expected wins

- eliminate the resource-tracker process for JETOS-native regions;
- eliminate name collisions and unlink bookkeeping for ordinary shared memory;
- safer crash cleanup;
- explicit transfer/rights model compatible with future JETOS capability objects.

### Fallback

`multiprocessing.shared_memory.SharedMemory` and the normal resource tracker.

### Acceptance test

Shared-memory semantics preserved across fork/spawn/process exit/crash tests; no leaked regions after process death; fewer helper processes and IPC messages.

---

## Experiment 6 — `jet_temp`: atomic unique temporary object creation

**Primary stdlib:** `tempfile`

### Current impedance mismatch

`tempfile.mkstemp()` and `mkdtemp()` generate randomized candidate names and retry creation with exclusive semantics until one succeeds. Temporary-directory discovery also probes candidates by creating/writing/deleting a test file.

### Proposed primitive

```text
jet_temp_create(dir_handle/path, kind, prefix, suffix, flags) -> {handle, generated_name?}
```

The filesystem/kernel allocates a collision-free temporary object atomically. Callers may request anonymous lifetime, a generated visible name, or an object that is published/linked later.

### Expected wins

- no randomized retry loop for uniqueness;
- no userspace race window between naming decisions and creation;
- anonymous lifetime can be tied directly to an fd/handle;
- simpler cleanup semantics for temporary files used only by one process.

### Fallback

Normal `tempfile` implementation and Linux `O_TMPFILE` where CPython already uses it.

### Acceptance test

Pass the complete tempfile test suite, including prefix/suffix and bytes-path behavior; lower creation latency under high concurrency with no collisions.

---

# Execution order

1. **`jet_spawn`** — highest combination of code simplification, race reduction, and measurable latency.
2. **`jet_waitset`** — broad leverage across asyncio/network/process control.
3. **`jet_memregion`** — deletes an entire helper-process/lifetime-management subsystem for the native path.
4. **`jet_copy`** — straightforward benchmarkable filesystem win.
5. **`jet_walk`** — especially relevant because JETOS itself repeatedly scans large source/file trees.
6. **`jet_temp`** — small, clean primitive and useful concurrency benchmark.

`tools/kernel_codesign_baseline.py` records the current stdlib behavior/performance envelope for all six experiments. The initial phase deliberately benchmarks the normal Python 3.14 paths before any kernel patch is accepted.
