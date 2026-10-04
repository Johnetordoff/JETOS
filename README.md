# JETOS — John E Tordoff's Operating System

JETOS is a source-oriented operating-system project built around **JETOS Language**, an editable fork of the latest stable CPython release. Linux is the initial native kernel substrate; JETOS Language is intended to own as much operating-system behavior as can correctly execute above that substrate.

The core rule is:

> **If JETOS Language can do it correctly, JETOS Language does it.**

JETOS-owned Python code uses only the Python/JETOS Language standard library and other JETOS-owned modules. Measured hot primitives may be implemented as small readable C extensions while retaining a Python-facing API.

**Current state:** early bootstrap. The repository contains reproducible kernel/language/rootfs build tooling, a Python PID-1 path, hardware capability discovery, a Tkinter reference desktop, Dunicode experiments, a C++→C compiler experiment, and a new subinterpreter service supervisor. A complete graphical QEMU boot has not yet been executed in this ChatGPT environment.

---

## 1. Operating-system model

JETOS aims to become the software system that owns a supported machine after firmware/boot handoff.

A mature JETOS installation should:

1. select and boot its kernel;
2. discover the actual machine instead of assuming a device type;
3. expose discovered hardware as explicit capabilities;
4. start a JETOS Language supervisor as PID 1;
5. run OS services and applications in JETOS Language wherever possible;
6. provide graphics, input, storage, networking, audio, power, cameras, sensors, containers, and other capabilities only when present/allowed;
7. trace every installed file back to source/build/provenance;
8. rebuild reproducibly from pinned source inputs;
9. support x86-64 and ARM64 first;
10. eventually install on real hardware rather than depending on Docker or a hypervisor.

Linux, QEMU, Docker, Gentoo, GCC, Tcl/Tk, and libc are current substrate or build inputs. They are not JETOS's identity.

---

## 2. Language constitution

JETOS-owned executable logic follows this order:

1. **JETOS Language first.**
2. **C** when the operation needs a native boundary or measured native performance.
3. **Assembly** only when architecture/boot requirements demand it.
4. **C++ is migration debt**, not an accepted new JETOS implementation language.

Canonical phrases:

> No mysterious files.  
> No mysterious build steps.  
> No mysterious languages.

> Python for JETOS logic.  
> C for native implementation.  
> Assembly only where architecture demands it.  
> C++ is migration debt.

> Git is history. Hosting is optional.

---

## 3. JETOS Language

JETOS Language is the operating system's normal implementation language, shell language, service language, build language, and application language.

It begins as a directly editable CPython fork so JETOS can absorb modern Python improvements while changing the interpreter/compiler/runtime when OS requirements justify it.

### Current stable base

JETOS tracks **stable Python only**.

Current pin:

```text
Python version: 3.14.8
Upstream: https://github.com/python/cpython.git
Commit: 8e6e75d9102e39bed2a2b279203a396741180f12
Release date: 2026-09-30
JETOS Language version: 0.2
```

Do not pin CPython `main`, alpha, beta, or release-candidate source as the JETOS base.

When Python.org publishes a newer stable release, updating the JETOS base becomes priority maintenance work. Check freshness with:

```bash
python jetos.py language-check
```

The checker uses only the standard library (`urllib`) and compares the pinned release to Python.org's latest stable Python 3 release.

### First interpreter-owned changes

The source fork changes CPython itself so the built runtime reports:

```python
sys.implementation.name == "jetos"
sys.jetos_language_version == "0.2"
sys.jetos_python_base_version == "3.14.8"
```

The fork retains the standard-library isolated-interpreter API and tests it during the language smoke test.

### Editable means editable

JETOS may modify:

- parser and grammar;
- compiler pipeline;
- bytecode and evaluator;
- object model;
- memory management and garbage collection;
- import system;
- standard library;
- Dunicode/Unicode integration;
- C extension boundaries;
- threading/subinterpreter behavior;
- startup assumptions;
- OS-native built-ins.

Compatibility with contemporary Python is valuable, but the long-term requirement is JETOS correctness and inspectability rather than permanent byte-for-byte CPython identity.

---

## 4. Standard-library-only Python rule

JETOS-owned Python code may import only:

- Python/JETOS Language standard-library modules; and
- JETOS-owned modules in this repository.

Do not add pip/PyPI runtime dependencies, `requirements.txt`, Poetry, uv, Conda, or vendored third-party Python packages to implement JETOS behavior.

Tkinter is allowed because it is the standard-library GUI API. Tcl/Tk underneath it is an explicit native dependency/substrate rather than a hidden Python package.

This rule is enforced by:

```bash
python tools/test_policy.py
```

The policy test parses every tracked Python file with `ast`, checks imports against `sys.stdlib_module_names` plus JETOS modules, rejects common third-party dependency manifests, and verifies that the development image and language fork are pinned to Python 3.14.8 stable.

Agent-specific development rules are in `AGENTS.txt`.

---

## 5. Main interpreter + subinterpreters

JETOS now models the operating system as **one main supervisor interpreter with isolated service subinterpreters**.

Conceptually:

```text
Linux kernel / native substrate
            ↓
JETOS Language main interpreter (PID 1)
            ↓
      OS supervisor model
            ↓
   ┌────────┼─────────┬─────────┐
   ↓        ↓         ↓         ↓
display   network   storage    audio   ...
interp    interp     interp     interp
```

The main interpreter owns the global JETOS model and remains alive rather than being replaced by a second REPL process.

Python 3.14's standard-library `concurrent.interpreters` API supplies the first implementation. Service interpreters communicate by explicit cross-interpreter queues/message passing.

### Default granularity

By default JETOS plans one interpreter for each present capability domain, including:

- display;
- network;
- wireless;
- Bluetooth;
- storage;
- audio;
- input;
- camera;
- battery/power;
- virtualization;
- serial.

JETOS may choose one interpreter per physical device when measurement, isolation, ownership, or failure containment makes that useful. Interpreter-per-device is an available strategy, not an unconditional rule.

Inspect the plan for the current machine:

```bash
python jetos.py interpreters
```

On Python/JETOS Language 3.14+, actually start and ping the planned service interpreters:

```bash
python jetos.py interpreters --run
```

To inspect the finer device-evidence split:

```bash
python jetos.py interpreters --per-device
```

### Why this is useful

Isolated CPython interpreters have separate interpreter state. When combined with separate OS threads, modern CPython subinterpreters can execute across CPU cores without sharing one interpreter GIL.

That provides an actor-like model:

- explicit ownership;
- explicit message passing;
- less accidental global state;
- potential multi-core execution;
- one operating-system process rather than many unrelated language runtimes.

Subinterpreters are **not a security sandbox**. Native code exists in the same process and extension modules can violate isolation.

Any JETOS C extension intended for multiple service interpreters must be designed for multiple-interpreter safety instead of assuming process-global Python state.

---

## 6. Native performance model

JETOS does not equate a Python API with slow implementation.

Start with readable JETOS Language:

```python
screen.blit(buffer, x, y)
storage.read(block)
audio.mix(frame)
```

Measure the real workload. If a primitive is hot, move that primitive into a small readable C extension while preserving the JETOS Language API.

Native strategies may include:

- buffer/memory operations in C;
- releasing the GIL around long-running native work when safe;
- subinterpreters on separate threads;
- optional CPython `--disable-gil` free-threaded builds for measured experiments;
- atomics/locks at explicit native boundaries;
- specialized bytecode/runtime changes in the JETOS Language fork.

The default is not "rewrite everything in C". It is **Python control + measured native primitives**.

---

## 7. Boot model

The intended first boot path is:

```text
firmware / virtual firmware
        ↓
JETOS-selected Linux kernel
        ↓
Python-generated initramfs/rootfs
        ↓
/init
        ↓
JETOS Language main interpreter as PID 1
        ↓
hardware discovery
        ↓
capability service subinterpreters
        ↓
JETOS graphical desktop
```

The main interpreter remains the supervisor. The diagnostic console runs inside that interpreter instead of `exec()` replacing it, so service subinterpreters can remain alive.

Native boundaries still required before JETOS Language can execute include CPU reset/firmware, boot handoff, kernel/architecture code, drivers, libc/loader, the interpreter's native implementation, filesystem implementation, and machine-code compilation.

JETOS does not pretend those layers are Python; it makes them visible and tries to minimize/own them.

---

## 8. Hardware capability discovery

JETOS asks Linux what hardware/capabilities the kernel actually exposes rather than assuming "desktop", "laptop", or "server" from a product name.

Current discovery inspects Linux-visible evidence such as:

- `/sys/class/net`;
- `/sys/class/ieee80211`;
- DRM connectors/modes;
- framebuffers;
- `/sys/block`;
- `/sys/class/sound`;
- `/sys/class/input`;
- `/sys/class/power_supply`;
- `/sys/class/bluetooth` / rfkill evidence;
- `/dev/video*` cameras;
- `/dev/kvm`;
- serial devices;
- `/proc/meminfo`;
- ACPI and Device Tree presence.

Each capability records:

```text
present
active
evidence
```

Long term the full state model is:

```text
capability exists
implementation installed
policy permits it
currently active
```

The desktop application registry is generated from discovered capabilities. Terminal/System diagnostics remain universal; network/display/audio/camera/power/etc. appear because the machine exposes them.

Future hot-plug work should use kernel uevents/netlink/DRM events rather than polling shell commands.

---

## 9. Desktop and Tkinter

The first standard JETOS desktop uses **Tkinter** because it is the GUI API in the language standard library.

Current reference aesthetic: a simple Windows-95/98-era interaction style implemented with JETOS-owned code/assets:

- black startup splash;
- teal/patterned background;
- gray beveled controls;
- dark-blue title bars;
- taskbar;
- Start-style launcher;
- clock;
- capability-derived applications;
- Terminal/System diagnostics.

Preview on a host with Tk:

```bash
python jetos.py gui
python jetos.py gui --geometry 640x480
python jetos.py gui --geometry 517x301
python jetos.py gui --fullscreen
```

The desktop is resolution-independent. 640×480 is only a visual reference, not a required display size. Layout is separately testable across tiny, portrait, ultrawide, 4K, 8K, and deliberately odd custom geometries.

Current Linux Tk stack:

```text
JETOS Language
    ↓
tkinter
    ↓
_tkinter
    ↓
Tcl/Tk
    ↓
window-system/display backend
```

Tcl/Tk/X11 are current native substrate, not immutable JETOS architecture.

A full graphical QEMU boot still needs the guest virtual-GPU/display backend joined to this desktop path.

---

## 10. Dunicode and Unicode

JETOS supports Unicode interoperability and an experimental JETOS-native **Dunicode** layer.

Current Dunicode v0.2 rules:

- one-to-one mapping to valid Unicode scalar values;
- strict UTF-8 serialization;
- `D+XXXX` notation;
- no silent normalization;
- invalid surrogate/out-of-range values rejected;
- malformed UTF-8 rejected;
- a scalar may be retired from **new canonical encoding** while historical bytes remain decodable to the original scalar.

That last property is intended to let a newer Dunicode convention remove a character without silently redefining old data as a different character/presentation.

Raw bytes remain raw bytes. Imported non-UTF-8 POSIX filenames must remain round-trippable.

---

## 11. Kernel direction

Linux is the initial JETOS kernel substrate.

JETOS-owned Python currently controls:

- kernel source pinning;
- required configuration profile;
- configuration patching;
- Kbuild invocation/orchestration;
- output selection;
- initramfs/rootfs creation;
- VM launch.

Current pinned Linux source:

```text
Linux stable: 6.12.96
Repository: https://github.com/gregkh/linux.git
Commit: 6d15a1029d425b15c59463910ebdccc4afe760d6
```

The kernel itself remains native C/assembly/Rust where upstream uses those languages. Kernel-adjacent work that can correctly live in JETOS Language should move there.

---

## 12. Compiler and C++ migration

JETOS treats the native compiler/toolchain as editable source, not a sealed appliance.

C++ is not accepted as new JETOS-owned implementation. Imported C++ is migration debt.

The first concrete GCC migration experiment is:

```text
ports/gcc/ordered_hash_map_c/
```

Pinned upstream provenance:

```text
GCC repository: gcc-mirror/gcc
GCC commit: 4bf11aca586c9eef753b6f76d29ae19e1b505694
ordered-hash-map.h blob: 3331394d985820d10ad2150a1c35ceec8f13985b
ordered-hash-map-tests.cc blob: b033bc5b7c2c7013cd5b54fd0eef3bb43b85ad16
```

The readable C11 replacement has passed 91 behavioral checks and sanitizer testing in the earlier bootstrap work.

This does **not** mean all GCC C++ has been converted or that GCC currently uses the replacement. The next meaningful compiler milestone is integrating a C replacement into a real GCC call path and rebuilding/running native GCC tests.

The experiment remains GPL-derived; source headers retain that provenance. Distribution/conveyance must satisfy the applicable GPL obligations even though the duplicate full license-text file was removed from this private bootstrap repository.

---

## 13. Gentoo and imported source

Gentoo is useful as source-oriented upstream/build infrastructure. It is not JETOS's identity.

Imported code should eventually have a build capsule recording:

- exact upstream revision/hash;
- dependency graph;
- build flags;
- toolchain;
- patches;
- licenses;
- source/build languages;
- whether Bash/C++ was required;
- produced runtime files;
- production-image permission.

Build environments may contain quarantined languages/tools forbidden for JETOS-owned source. Released runtime content should be explicit and minimal.

---

## 14. Networking

JETOS intends one master networking policy switch with explicit strength states such as:

```text
ON
OFF_VERIFIED
OFF_SOFTWARE_ENFORCED
OFF_UNVERIFIED
ERROR
```

The first QEMU boot configuration presents **no virtual NIC**, making networking-off true at the guest hardware boundary for that test configuration.

Later OFF behavior should cover interfaces, routes, ingress/egress firewalling, existing connections, radios/rfkill, bridges/veth/container networks, and applications attempting to reverse policy.

Loopback/local Unix IPC may remain available.

---

## 15. Files and introspection

A mature JETOS build should classify every installed file with information such as:

- path/type/size/hash;
- owner/component;
- upstream project/version;
- source/build provenance;
- license;
- architecture;
- JETOS-owned vs imported;
- source language;
- reason/capability for inclusion.

The desired trace is:

```text
source → build rule → artifact → installed file → image
```

Unclassified OS files are defects.

---

## 16. Docker, QEMU, and real hardware

Docker is an optional reproducible **build/development environment**.

QEMU/hardware virtualization provides a virtual **computer** on which JETOS can boot its own selected kernel/rootfs.

Neither is part of the final OS identity.

```text
JETOS source
   ├── Docker builder → QEMU → JETOS
   ├── native Linux builder → QEMU → JETOS
   └── image builder → physical machine → JETOS
```

Do not claim a VM test proves physical Wi-Fi/GPU/audio/suspend/etc. Those require bare-metal hardware validation.

---

## 17. Architectures

Initial targets:

- x86-64;
- ARM64/AArch64.

RISC-V64 may come later. Initial 32-bit support is not a goal.

Architecture-specific native code should remain isolated from the JETOS Language-facing behavior model.

---

## 18. Development workflow

After cloning:

```bash
git clone https://github.com/Johnetordoff/JETOS.git
cd JETOS
python jetos.py doctor
python jetos.py test
python jetos.py language-check
python jetos.py dev
```

Useful commands:

```bash
python jetos.py gui --geometry 640x480
python jetos.py interpreters
python jetos.py interpreters --run
python jetos.py interpreters --per-device
python jetos.py text
python jetos.py setup --plan
```

`python jetos.py dev` uses Docker by default; Linux can use `--native`.

Host setup tooling supports macOS/Homebrew, common Linux package managers, and Windows/winget + Docker Desktop. It is a development/VM setup tool, **not a destructive bare-metal installer**.

---

## 19. Tests

Current repository tests include:

```text
tools/test.py
tools/test_unicode.py
tools/test_language.py
tools/test_bootstrap.py
tools/test_capabilities.py
tools/test_desktop.py
tools/test_policy.py
tools/test_interpreters.py
```

They cover the C experiment, Unicode/Dunicode, language source transformation, rootfs/bootstrap pieces, synthetic Linux hardware discovery, arbitrary display geometries, standard-library-only policy, and subinterpreter planning/live behavior when run on Python 3.14+.

A test result is not interchangeable with a VM or bare-metal result. Keep claims explicit:

```text
implemented
static/unit tested
dry-run tested
VM boot tested
bare-metal tested
```

---

## 20. Repository layout

JETOS intentionally keeps authored source small. Imported source trees and generated artifacts belong under `.build/`.

```text
AGENTS.txt
Dockerfile
README.md
jetos.py
src/jetos/
    __init__.py
    apps.py
    desktop.py
    dunicode.py
    hardware.py
    init.py
    interpreters.py
    startup.py
tools/
    build.py
    dev.py
    host.py
    language.py
    python_release.py
    test*.py
ports/gcc/ordered_hash_map_c/
    ordered_hash_map.c
    ordered_hash_map.h
    test_ordered_hash_map.c
```

`README.md` is the canonical architecture Markdown file. `AGENTS.txt` is the machine/human development constitution for future coding agents.

---

## 21. Current limitations

Do not overstate the current implementation:

- the full kernel + initramfs + JETOS Language QEMU boot has not been executed in this ChatGPT runtime because QEMU/Docker execution is unavailable here;
- the Tk desktop has not yet been shown inside the JETOS QEMU guest because the guest display/window-system boundary is unfinished;
- the subinterpreter supervisor is implemented against Python 3.14's standard-library API, but a complete JETOS Language 3.14.8 build has not been compiled in this ChatGPT runtime;
- the compiler C++→C work covers one experiment, not the whole compiler;
- networking OFF beyond the no-NIC VM configuration is not complete;
- bare-metal installation/recovery is not ready.

---

## 22. Near-term milestones

1. Build JETOS Language from the pinned Python 3.14.8 source.
2. Run the language smoke test, including isolated-interpreter creation.
3. Boot the generated kernel/initramfs under QEMU.
4. Verify PID 1 is the JETOS main supervisor interpreter.
5. Verify capability service subinterpreters start and communicate.
6. Add the guest virtual GPU/display backend.
7. Show the same Tkinter desktop inside the VM.
8. Add kernel event-driven capability changes (uevents/netlink/DRM).
9. Measure service/GUI/storage hot paths before introducing native C extensions.
10. Integrate a real C++→C compiler replacement into the actual compiler build.
11. Implement stronger networking-OFF verification.
12. Repeat boot/display behavior on ARM64 and selected physical test hardware.

---

## 23. Canonical shorthand

> JETOS Language is the operating system language.

> Track the latest stable Python, then make it ours.

> Standard library first; no PyPI runtime stack.

> One main supervisor interpreter; isolated subinterpreters for services where useful.

> Discover the machine. Declare its capabilities. Build the UI and services from evidence.

> Write behavior in JETOS Language. Measure it. Move only hot/native primitives into readable C.

> Docker builds it. A hypervisor boots it. Physical hardware proves it.
