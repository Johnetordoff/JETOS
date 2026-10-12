# JETOS standard-library-first reduction rule

JETOS reduces the operating-system substrate around the language. It does **not** reduce the JETOS/Python language or standard library merely to make the operating system smaller.

The protected compatibility surface is the complete standard-library surface supported by the selected JETOS/CPython build on Linux. Linux configuration, drivers, native libraries, rootfs contents, services, and other OS substrate may be reduced only when the same language surface still qualifies afterward.

## Order of work

1. Build the JETOS language on the full known-good substrate.
2. Run the fast host-side qualification with the JETOS runtime to catch language-build failures and record a baseline surface manifest.
3. Boot a dedicated JETOS qualification image with `python tools/stdlib_guest.py`. This runs the same qualification **inside JETOS against JETOS's own kernel and rootfs**. This guest result is authoritative for OS-substrate work.
4. Before accepting an OS reduction, boot the reduced candidate through the same guest qualification path and compare its language surface with the known-good baseline.
5. For a reduction candidate intended to become canonical, run `python tools/stdlib_guest.py --full` so CPython's installed regression suite also exercises standard-library behavior inside JETOS.
6. Reject or revise any OS reduction that removes an applicable stdlib module, changes the callable surface unexpectedly, breaks a capability probe, or fails the regression suite.

## What the fast qualification does

The fast qualification:

- imports every applicable top-level module named by `sys.stdlib_module_names` in an isolated interpreter;
- inventories every callable symbol exposed by each imported module, including class methods, and records signatures where introspection supports them;
- exercises safe representative OS-backed behavior including files, subprocesses, threads, asyncio, sockets, IPv4/IPv6 loopback, selectors, PTYs, mmap, compression, hashing, dbm, SQLite, OpenSSL, ctypes, curses, Tcl/Tk, and JSON;
- can write a deterministic JSON language-surface manifest;
- can compare a candidate OS against a known-good manifest.

A generic harness must not blindly invoke every callable. The standard library deliberately exposes operations such as process termination/replacement, forking, signal manipulation, server creation, filesystem mutation, and external I/O. Calling arbitrary functions with guessed arguments would be both unsafe and a poor correctness test. Behavioral qualification therefore combines explicit safe probes with CPython's own regression suite rather than pretending that one synthetic call per function is sufficient.

## Host versus guest evidence

The host-side qualification is an early build check only. It proves that the built JETOS language works against the build host's Linux substrate. It cannot prove that a reduced JETOS kernel/rootfs still provides the same capabilities.

For OS whittling, only the booted guest qualification counts as substrate evidence. A candidate does not pass merely because its JETOS runtime worked on the build host.

## Governing invariant

**Python is the fixed compatibility surface; the OS is the variable.**

If an OS reduction breaks the JETOS/Python standard library, the reduction went too far. The response is to restore the required OS capability, not to trim the language to match the smaller substrate.
