# JETOS Requirements and Bootstrap Architecture

**Document:** JETOS Requirements  
**Version:** 0.2  
**Status:** Living design document — v0.2  
**Date:** 2026-10-03  
**Purpose:** Define the smallest practical Gentoo-derived Linux substrate on which JETOS can be built, while keeping JETOS itself Python-first and portable across reasonable computers, phones, tablets, and purpose-built devices.

---

## 1. Executive decision

JETOS will initially use **Gentoo as a bootstrap source ecosystem and build substrate, not as the permanent identity or user-facing architecture of JETOS**.

The initial target is not "a customized Gentoo desktop." It is a **minimal Linux system that can:**

1. boot on explicitly supported hardware;
2. mount a normal local filesystem;
3. discover the machine and its capabilities;
4. run current stable CPython;
5. provide a JETOS-owned networking API;
6. communicate using standard network protocols;
7. support a complete software network-off switch;
8. provide the Linux kernel facilities required for OCI/Docker-like application containers;
9. omit a required graphics stack, audio stack, desktop environment, and general-purpose GUI;
10. leave deliberate extension points for future JETOS graphics, audio, input, application, and UI APIs.

Gentoo is useful here because its package manager, Portage, is already written in Python, its system configuration is highly decomposable, it supports multiple CPU architectures, and its profile mechanism can define a sharply reduced base system.

JETOS should **not** begin as a blind copy of the entire Gentoo repository. The first implementation should use:

- Gentoo sources/packages where they are useful;
- a JETOS Gentoo profile and JETOS overlay/repository;
- JETOS build scripts;
- JETOS hardware profiles;
- JETOS Python control software;
- upstream Linux;
- only the minimum imported userspace needed to boot and bootstrap JETOS.

Long term, Gentoo components may be removed, rewritten, or replaced as JETOS gains its own equivalents.

---

## 2. Language rule

### JETOS-REQ-001 — Python first

All JETOS-owned implementation code MUST be written in Python wherever rational.

Preferred implementation order:

1. Python standard library;
2. optimized Python;
3. CPython C extension or direct C interoperability where the operating system or hardware boundary requires it;
4. assembly only where neither Python nor C can correctly implement the required low-level operation.

Declarative data and configuration files are exempt from the programming-language rule.

### JETOS-REQ-002 — Minimal runtime dependencies

JETOS-owned Python code SHOULD depend on the Python standard library wherever practical.

Third-party Python packages are not part of the base system unless specifically approved.

### JETOS-REQ-003 — Upstream substrate is not “JETOS code”

The language rule applies to software JETOS owns and maintains.

It does **not** imply rewriting the following before JETOS can boot:

- the Linux kernel;
- CPU firmware/microcode;
- device firmware;
- CPython itself;
- the C runtime;
- the compiler/linker toolchain;
- hardware drivers imported from Linux;
- transitional third-party software such as an OCI runtime.

Those are treated as substrate dependencies and may be replaced later if there is a reason to do so.

---

## 3. What “portable” means

### JETOS-REQ-010 — Hardware, not host-OS dependence

A native JETOS installation runs on hardware through Linux. It is not fundamentally dependent on Windows, macOS, Android, iOS, or another host operating system.

Hosted development versions of JETOS MAY run inside a VM, container, or compatibility environment on another operating system.

### JETOS-REQ-011 — Initial CPU architecture targets

The architecture must allow at least:

- x86-64 / amd64;
- ARM64 / AArch64.

Later candidates may include:

- RISC-V 64;
- other Linux-supported architectures where useful.

32-bit architectures are not an initial requirement.

### JETOS-REQ-012 — Device support is explicit

JETOS MUST distinguish between:

- **CPU architecture support**; and
- **actual device/board support**.

An ARM64 build does not imply that every ARM64 phone or tablet is supported.

A supported physical target requires a working path for:

- boot firmware / bootloader;
- Linux kernel;
- device tree or ACPI/platform description;
- storage;
- interrupt controller;
- timers;
- display hardware if display is required;
- input hardware if input is required;
- USB where required;
- network hardware where required;
- device-specific firmware.

### JETOS-REQ-013 — Capability model instead of “phone/tablet/computer” assumptions

JETOS SHOULD identify devices by capabilities rather than hard-coding product categories.

The JETOS hardware service should expose facts such as:

- CPU architecture;
- CPU count/features;
- RAM;
- storage devices;
- removable storage;
- battery presence;
- AC power state;
- display count/resolution/physical size where available;
- touch capability;
- keyboard capability;
- pointer capability;
- rotation/orientation sensors;
- cameras;
- microphones;
- speakers/audio hardware;
- Wi-Fi;
- Ethernet;
- Bluetooth;
- cellular modem;
- GPS/GNSS;
- GPU identity/capabilities;
- virtualization support;
- hardware security modules where available.

A higher-level classification such as `desktop`, `laptop`, `tablet`, `phone`, `handheld`, or `server` MAY be inferred, but applications should prefer capabilities.

### JETOS-REQ-014 — Hardware discovery backend

On Linux, JETOS hardware discovery may use information exposed through:

- sysfs;
- procfs;
- ACPI;
- Device Tree;
- PCI;
- USB;
- kernel netlink/uevent interfaces.

JETOS should wrap these in one stable Python API rather than exposing Linux-specific discovery paths to normal applications.

---

## 4. Gentoo bootstrap policy

### JETOS-REQ-020 — Gentoo is bootstrap infrastructure

JETOS may consume Gentoo packages and metadata without presenting the resulting system as Gentoo.

Gentoo package sources should be treated as upstream inputs with their provenance and licenses preserved.

### JETOS-REQ-021 — JETOS profile

Create a dedicated JETOS Gentoo profile whose defaults remove unnecessary desktop/general-purpose features.

The profile should begin from the smallest stable architecture-appropriate profile that remains practical.

Do **not** globally disable every Gentoo USE flag with `-*` without auditing dependencies. Gentoo explicitly warns that doing so can break assumptions encoded by package maintainers.

### JETOS-REQ-022 — JETOS overlay/repository

JETOS SHOULD have its own repository/overlay containing:

- the JETOS profile;
- JETOS packages;
- JETOS patches;
- JETOS configuration;
- device profiles;
- build definitions;
- compatibility shims;
- replacements for Gentoo components as they are rewritten.

### JETOS-REQ-023 — Development vs runtime images

JETOS SHOULD produce at least two image classes.

**Development image**
- compiler/toolchain;
- headers;
- Portage/bootstrap tooling;
- source/build support;
- debugging tools;
- Python development headers.

**Runtime image**
- no compiler by default;
- no complete Gentoo source tree by default;
- no Portage requirement after image creation unless deliberately retained;
- CPython runtime;
- JETOS runtime/control system;
- required shared libraries;
- kernel modules/firmware required for supported hardware;
- container support where enabled.

This prevents “source distribution” from meaning every device must carry a full build environment.

---

## 5. Minimal operating-system substrate

### JETOS-REQ-030 — Linux kernel

The initial JETOS kernel is Linux.

JETOS should track a modern supported upstream/stable kernel rather than an artificially old compatibility baseline.

### JETOS-REQ-031 — Required kernel facilities

The baseline kernel must include the facilities needed for:

**Boot and process operation**
- ELF executable loading;
- virtual memory;
- process/thread creation;
- signals;
- timers;
- procfs;
- sysfs;
- devtmpfs;
- tmpfs;
- pseudo-terminals;
- Unix-domain sockets;
- inotify/fanotify as required.

**Filesystem**
- ext4 baseline;
- FAT/VFAT support where EFI boot requires it;
- OverlayFS for container/application layering;
- optional F2FS later for flash-focused devices.

**Device discovery**
- uevents;
- ACPI on appropriate systems;
- Device Tree on appropriate systems;
- PCI;
- USB;
- platform buses required by supported devices.

**Security**
- Linux capabilities;
- seccomp;
- user namespaces where supported;
- mount namespaces;
- PID namespaces;
- IPC namespaces;
- UTS namespaces;
- network namespaces;
- cgroup v2;
- required LSM support to be selected later.

**Networking**
- network device framework;
- IPv4;
- IPv6;
- TCP;
- UDP;
- Unix sockets;
- netlink;
- packet filtering support;
- nftables/netfilter support;
- Ethernet;
- Wi-Fi stack only on device profiles that need it;
- Bluetooth only when explicitly enabled;
- cellular interfaces only on supported device profiles.

### JETOS-REQ-032 — Minimal filesystem choice

The initial ordinary root filesystem SHOULD be ext4.

Reasons:

- mature;
- widely supported;
- easy to repair and inspect;
- works well with the intended minimal baseline;
- compatible with typical container storage arrangements.

A device profile may substitute another filesystem when hardware characteristics justify it.

---

## 6. Boot and init

### JETOS-REQ-040 — Boot is platform-specific behind a JETOS build interface

JETOS MUST NOT pretend that one boot image can boot every machine.

At minimum, expect different boot paths for:

- UEFI x86-64 systems;
- ARM64 systems using UEFI;
- ARM64 boards using U-Boot;
- vendor-specific mobile boot chains.

The build system should hide those differences behind a common device-profile interface.

### JETOS-REQ-041 — Transitional init is allowed

Early JETOS builds MAY use an existing init/bootstrap mechanism while JETOS is being brought up.

Long term, the preferred design is a JETOS-owned process supervisor implemented primarily in Python.

A tiny native bootstrap/shim is acceptable if needed before CPython can start safely.

### JETOS-REQ-042 — Python PID 1 responsibilities

If JETOS eventually runs Python as PID 1 or as the primary system supervisor, it MUST correctly handle:

- orphaned child reaping;
- SIGCHLD;
- shutdown/reboot;
- service lifecycle;
- mount setup;
- device-event handling;
- crash recovery;
- emergency/rescue boot;
- logging before the normal logging system exists.

---

## 7. Python baseline

### JETOS-REQ-050 — Current stable CPython

JETOS should use the newest stable CPython version that has passed the JETOS compatibility test suite.

The project should move forward promptly when a new stable CPython release is validated.

### JETOS-REQ-051 — Python must be a first-class system runtime

The base runtime image must be able to:

- run Python from local storage;
- import the standard library;
- launch child processes;
- use local files;
- use sockets through the JETOS networking layer;
- load approved native JETOS extensions;
- introspect hardware through the JETOS hardware layer.

### JETOS-REQ-052 — No shell required by normal JETOS applications

A POSIX shell may remain in bootstrap/development images, but normal JETOS applications should not require shell scripts.

Long term, Gentoo ebuild/bash requirements are a bootstrap concern, not a JETOS application API.

---

## 8. Networking

### JETOS-REQ-060 — JETOS owns the public networking API

Normal JETOS applications should use a JETOS networking API rather than being designed directly around Linux-specific networking details.

Initial implementation may use Python's socket facilities and Linux kernel networking beneath that API.

The public API should be designed so that a hosted JETOS runtime could later provide a different backend on another host.

### JETOS-REQ-061 — Standards compatibility

JETOS networking must interoperate with ordinary machines and networks.

The initial protocol expectations are:

- Ethernet where hardware supports it;
- Wi-Fi where hardware supports it;
- IPv4;
- IPv6;
- TCP;
- UDP;
- DNS;
- DHCP where required for ordinary network attachment;
- TLS through an approved implementation;
- HTTP support may be provided at a higher layer.

JETOS does not need to reimplement TCP/IP in Python merely to own its public API. The Linux kernel network stack may implement transport/network protocols underneath JETOS.

### JETOS-REQ-062 — Single master networking switch

JETOS MUST expose one master user-visible network state:

- `ON`
- `OFF`

When `OFF`, the intent is **no external communications of any kind**.

The implementation must be fail-closed and should perform all applicable actions atomically or transactionally:

1. prevent new external network sockets/connections;
2. terminate or freeze existing external network connectivity;
3. administratively disable network interfaces;
4. remove external routes;
5. install a kernel-level drop policy for ingress/egress;
6. block Wi-Fi radios through rfkill where supported;
7. block Bluetooth radios through rfkill where supported;
8. disable cellular modem data/radio through the supported device backend where possible;
9. disable container bridges, veth endpoints, and container external connectivity;
10. prevent unprivileged applications from reversing the state.

### JETOS-REQ-063 — Network-off verification

The network switch must report whether the desired state has been verified.

Suggested states internally:

- `ON`
- `OFF_VERIFIED`
- `OFF_SOFTWARE_ENFORCED`
- `OFF_UNVERIFIED`
- `ERROR`

The normal UI may still show a simple ON/OFF switch, but diagnostic tools must reveal the actual guarantee.

This distinction is required because not every physical device exposes a software-controllable hard radio kill mechanism.

### JETOS-REQ-064 — Strict OFF semantics

For the first implementation, `OFF` means:

- no packets may leave or enter through physical or virtual external interfaces;
- container networking is disabled;
- Wi-Fi/Bluetooth/cellular radios are disabled when controllable;
- the system remains capable of local process IPC.

Unix-domain sockets remain available.

Loopback (`127.0.0.1` / `::1`) MAY remain enabled because it does not communicate off-device. If JETOS later requires literal elimination of all IP networking including loopback, that can be introduced as a stricter engineering mode without changing the user-visible master switch.

---

## 9. Containers and application isolation

### JETOS-REQ-070 — Container capability is part of the kernel baseline

JETOS must retain the kernel primitives required for OCI/Docker-like containers even if Docker itself is not installed.

Required concepts include:

- namespaces;
- cgroup v2;
- capabilities;
- seccomp;
- OverlayFS or equivalent image layering;
- virtual Ethernet/network namespaces when networking is enabled.

### JETOS-REQ-071 — Docker is compatibility, not architecture

Docker Engine MAY be used during development and MAY be packaged for JETOS.

JETOS must not make Docker's API or daemon a permanent architectural dependency.

A future JETOS application-container runtime may be implemented in Python plus approved native extensions directly over Linux kernel primitives.

### JETOS-REQ-072 — Containerized graphical applications are anticipated

The future application model must permit a containerized game or graphical application to receive controlled access to:

- GPU;
- display surface;
- input devices;
- audio;
- filesystem;
- network;
- controllers;
- clocks/timers.

These capabilities must be individually grantable.

A container should not receive unrestricted host device access merely because it needs graphics.

### JETOS-REQ-073 — Cross-architecture limitation

A container image compiled for a different CPU instruction set cannot run natively merely because it is in a container.

Cross-architecture execution requires translation/emulation or recompilation.

JETOS should prefer native architecture builds.

---

## 10. Graphics

### JETOS-REQ-080 — No mandatory user-facing graphics API in baseline v0

The first bootable JETOS base does not require a desktop environment, X11, Wayland compositor, Qt, GTK, or a browser.

A serial console or text console is sufficient for baseline bring-up.

### JETOS-REQ-081 — JETOS will define its own graphics API

Applications should ultimately target a JETOS graphics API.

Linux graphics interfaces are implementation backends, not the public JETOS application contract.

### JETOS-REQ-082 — Practical future backend

The future graphics implementation may use some combination of:

- Linux DRM/KMS for displays and buffer/display management;
- kernel GPU drivers;
- Vulkan as a portable GPU execution backend where supported;
- Mesa or vendor user-space drivers where required.

This does not make Vulkan, DRM, or Mesa the JETOS application API.

### JETOS-REQ-083 — Hardware-specific acceleration allowed

Known hardware may receive specialized JETOS backends.

A specialized backend must still implement the common JETOS graphics contract.

This preserves the earlier JETOS principle that known hardware, including Apple Silicon-class targets where Linux support exists, may be specially optimized without forcing applications to know the hardware.

---

## 11. Audio

### JETOS-REQ-090 — No mandatory audio system in baseline v0

The first minimal JETOS runtime may omit user-facing audio entirely.

### JETOS-REQ-091 — JETOS will define its own audio API

Future applications should use a JETOS audio API.

The implementation may use Linux ALSA/kernel audio interfaces or other platform-specific mechanisms beneath that API.

PipeWire or PulseAudio are not mandatory architectural dependencies.

---

## 12. Input

### JETOS-REQ-100 — Input belongs to JETOS capability APIs

The future input API must support at minimum:

- keyboard;
- pointer/mouse;
- touch;
- controller/gamepad.

Later:
- stylus;
- accelerometer;
- gyroscope;
- haptics;
- specialized sensors.

Linux evdev/input interfaces may be backend mechanisms.

---

## 13. Package and application model

### JETOS-REQ-110 — Gentoo packages are an upstream source pool

JETOS may initially rely on Gentoo to compile imported software.

JETOS should record for every imported package:

- upstream source;
- exact version;
- JETOS patches;
- build options;
- license;
- source hash;
- architecture;
- binary hash.

### JETOS-REQ-111 — Reproducibility

The build system should be deterministic/reproducible where practical.

A JETOS image should be reconstructable from:

- JETOS source revision;
- device profile revision;
- package/source lock information;
- kernel configuration;
- toolchain identity.

### JETOS-REQ-112 — Application isolation by default

Long term, applications SHOULD be isolated from the host and granted capabilities explicitly.

Candidate capability grants include:

- display;
- GPU;
- sound output;
- microphone;
- camera;
- network;
- controller;
- filesystem paths;
- clipboard;
- location;
- Bluetooth;
- USB device.

---

## 14. Security model

### JETOS-REQ-120 — Least privilege

Normal applications must not run with unrestricted host privileges.

### JETOS-REQ-121 — Network switch cannot be overridable by applications

An ordinary application or container must not be able to turn networking back on when the JETOS master switch is OFF.

### JETOS-REQ-122 — Signed/update policy to be defined

The image/update signing scheme is not yet selected, but production JETOS images must eventually authenticate system updates.

### JETOS-REQ-123 — Rescue path

A broken JETOS Python runtime must not make the device permanently unrecoverable.

Supported production devices should have a documented recovery path, such as:

- alternate boot slot;
- recovery image;
- recovery partition;
- external flashing mechanism.

Exact mechanism is device-specific.

---

## 15. Firmware and non-free components

### JETOS-REQ-130 — Firmware is treated separately from JETOS code

Many GPUs and wireless devices require firmware.

A JETOS device profile must identify required firmware explicitly.

### JETOS-REQ-131 — License visibility

Firmware and imported packages must retain their own licensing information.

The JETOS build must not silently relicense imported software.

### JETOS-REQ-132 — Redistribution check

Before JETOS distributes an image containing a package or firmware blob, its redistribution terms must be checked.

Gentoo's ebuild `LICENSE` metadata can assist, but it must not be treated as a legal guarantee for every installed file.

---

## 16. Licensing and Gentoo provenance

### JETOS-REQ-140 — Preserve notices and licenses

Code copied or modified from Gentoo, Portage, Linux, or other upstream projects must retain the notices and license obligations required by the applicable source licenses.

Portage is GPL-2.0 licensed.

Gentoo projects commonly use GPL-compatible free-software licenses, while individual packages in the Gentoo repository retain their own upstream licenses.

### JETOS-REQ-141 — JETOS branding is separate

JETOS should use its own name and visual identity.

Gentoo's name and logo should be used only where needed to describe provenance, compatibility, build input, or upstream origin, subject to Gentoo's trademark/name usage rules.

### JETOS-REQ-142 — Fork history is not hidden

If JETOS imports Gentoo components, commit history and attribution should be preserved where practical.

The project should describe itself accurately, e.g. "initially bootstrapped from Gentoo sources" rather than implying independent authorship of imported code.

---

## 17. Initial image contents

The first successful JETOS runtime image should aim to contain only what is necessary for the selected device.

### Required

- Linux kernel;
- device-specific modules;
- required device firmware;
- boot artifacts;
- C runtime required by CPython and imported native components;
- dynamic loader if dynamically linked;
- CPython;
- Python standard library;
- JETOS init/supervisor or transitional bootstrap;
- JETOS hardware service;
- JETOS network service/API;
- certificate store if TLS is enabled;
- minimal filesystem tools required for recovery/boot;
- minimal logging;
- container kernel support.

### Optional / development only

- Portage;
- Bash;
- compiler;
- linker;
- make/build tools;
- source headers;
- SSH;
- Docker Engine;
- debugging tools.

### Explicitly not required in baseline v0

- X11;
- Wayland compositor;
- desktop environment;
- display manager;
- GTK;
- Qt;
- PipeWire;
- PulseAudio;
- web browser;
- office suite;
- printing;
- Bluetooth unless device profile asks for it;
- Wi-Fi unless device profile asks for it;
- GUI installer.

---

## 18. Suggested JETOS repository layout

```text
jetos/
├── README.md
├── REQUIREMENTS.md
├── LICENSES/
├── docs/
│   ├── architecture/
│   ├── devices/
│   ├── networking/
│   ├── graphics/
│   ├── audio/
│   └── containers/
├── src/
│   └── jetos/
│       ├── boot/
│       ├── hardware/
│       ├── network/
│       ├── process/
│       ├── containers/
│       ├── graphics/
│       ├── audio/
│       └── input/
├── python_extensions/
│   ├── hardware/
│   ├── kernel/
│   ├── graphics/
│   └── audio/
├── gentoo/
│   ├── overlay/
│   ├── profiles/
│   ├── package.use/
│   ├── package.mask/
│   └── package.license/
├── kernel/
│   ├── common/
│   └── devices/
├── devices/
│   ├── x86_64-generic/
│   └── arm64-generic/
├── images/
├── tools/
└── tests/
```

Assembly, if ever required, should live in a narrowly scoped architecture-specific subtree rather than spreading through the project.

---

## 19. Device profile contract

Each supported device or device family should have a declarative profile containing at least:

```text
id
cpu_arch
boot_method
kernel_config
kernel_patches
device_tree_or_acpi_expectation
firmware
storage_layout
root_filesystem
display_backend
input_backend
network_interfaces
radio_control_methods
gpu_backend
audio_backend
container_support
recovery_method
known_limitations
```

The generic x86-64 target can support a broad PC hardware class.

ARM/mobile targets should normally be specific device/board profiles until hardware support becomes standardized enough to generalize.

---

## 20. JETOS hardware abstraction rule

JETOS must separate:

### Application-facing API

Examples:

```python
jetos.hardware.displays()
jetos.hardware.has_touch()
jetos.network.status()
jetos.network.set_enabled(False)
jetos.graphics.create_surface(...)
jetos.audio.open_output(...)
```

### Linux backend

Examples:

- sysfs;
- netlink;
- rfkill;
- DRM/KMS;
- evdev;
- ALSA;
- cgroups;
- namespaces;
- ioctls;
- device-tree data.

Applications should not need to know which backend produced the result.

---

## 21. Why Gentoo remains a reasonable bootstrap choice

Gentoo has several unusually useful properties for this project:

1. Portage is already Python-based.
2. The distribution is source-oriented.
3. Profiles can define system-package and feature defaults.
4. USE flags let JETOS omit entire classes of unwanted functionality.
5. Gentoo supports amd64 and ARM/ARM64 and other architectures.
6. JETOS can maintain its own profile and overlay without immediately owning every upstream package recipe.
7. Development images can retain Portage while runtime images are aggressively reduced.

Gentoo is therefore useful as an **upstream build ecosystem** even if the finished JETOS runtime stops looking like Gentoo.

---

## 22. Why not simply use Buildroot as JETOS?

Buildroot is an excellent reference for creating tiny cross-compiled Linux systems. It can build a toolchain, kernel, bootloader, and root filesystem.

However, its own project documentation explicitly positions it primarily as a root-filesystem/build-image generator rather than a general distribution with package-level lifecycle management.

JETOS can borrow the useful design idea:

> define a target, cross-build a complete known image, and deploy the image as a unit

without making Buildroot the permanent JETOS package/application architecture.

A future decision may still use Buildroot tooling for certain appliance-like JETOS targets.

---

## 23. Things that are impossible or misleading to promise

### 23.1 “One image that boots on every phone/tablet/computer”

Not realistic.

CPU architecture is only one layer. Boot firmware, device trees, drivers, proprietary firmware, storage layout, secure boot, and locked bootloaders differ substantially.

### 23.2 “Everything is Python, including the Linux machine underneath”

Not while JETOS is Linux-based.

Python itself requires a native runtime and kernel services. The practical rule is that **JETOS-owned policy, APIs, services, and application framework are Python-first**, while Linux and required native substrate remain underneath.

### 23.3 “A Docker container makes CPU architecture irrelevant”

False.

Containers share the host kernel and normally require binaries compiled for the host CPU architecture.

### 23.4 “A software switch can physically guarantee every radio is electrically dead on every device”

Not on arbitrary hardware.

Linux rfkill provides a standard mechanism for radio blocking where drivers/hardware support it, including hard and soft block concepts. A JETOS software switch can guarantee packet denial at the kernel boundary and request radio shutdown, but some hardware may lack a verifiable software-controlled physical radio kill.

JETOS must report the guarantee level rather than pretending otherwise.

### 23.5 “No graphics stack is needed to eventually draw”

The baseline may omit graphics, but a future graphical system still needs:

- a display driver;
- memory/buffer management;
- GPU or software rendering;
- a route to the physical display.

JETOS may own the API, but it cannot render pixels without a hardware/backend mechanism.

---

## 24. Milestones

### Phase 0 — Specification

- [x] define Python-first rule;
- [x] define Linux substrate boundary;
- [x] define minimal runtime scope;
- [x] define networking master switch requirement;
- [x] define capability-based hardware model;
- [x] define container kernel requirement;
- [ ] choose exact first hardware target.

### Phase 1 — Generic x86-64 JETOS bootstrap

Goal: boot in a VM and one ordinary x86-64 machine.

Must demonstrate:

- boot;
- Python;
- filesystem;
- hardware inventory;
- networking ON;
- networking OFF;
- test TCP connection before OFF;
- prove connection fails after OFF;
- container kernel self-test;
- no desktop/audio stack.

### Phase 2 — ARM64 development target

Goal: boot the same JETOS userland/API on one explicitly selected ARM64 development board.

Must demonstrate identical JETOS hardware/network APIs.

### Phase 3 — Mobile-class target

Goal: boot on one selected phone/tablet-class device with documented bootloader and kernel support.

Add:

- battery;
- touch;
- orientation;
- radio controls;
- display backend.
### Phase 4 — JETOS application container

Run one application in an isolated container/capsule with:

- filesystem sandbox;
- CPU/memory limits;
- optional network grant;
- future display/input grant.

### Phase 5 — Graphics API

Create first JETOS graphics surface and draw without applications directly depending on X11/Wayland/GTK/Qt.

### Phase 6 — Audio API

Create first JETOS audio output path behind the JETOS API.

---

## 25. Phase-1 acceptance tests

A Phase-1 image is not “JETOS bootstrapped” until all of these pass:

1. boots from a clean image;
2. reaches JETOS supervisor;
3. reports CPU/RAM/storage;
4. launches current validated CPython;
5. imports the entire required standard-library subset;
6. reads and writes ext4 filesystem;
7. obtains a network address when networking is ON;
8. resolves DNS;
9. makes TCP and UDP test connections;
10. switches networking OFF through one JETOS call;
11. existing external network communication stops;
12. new external connections fail;
13. interfaces/routes/filter state match the OFF policy;
14. containers cannot bypass OFF;
15. re-enabling networking restores expected operation;
16. cgroup v2 works;
17. namespaces work;
18. OverlayFS works;
19. seccomp works;
20. a trivial containerized process runs;
21. image contains no required desktop environment;
22. image contains no required audio server;
23. all imported package/license metadata is recorded.

---

## 26. First implementation recommendation

The first practical JETOS system should be:

- amd64;
- UEFI;
- Linux;
- ext4;
- minimal Gentoo profile;
- JETOS overlay;
- CPython;
- no required GUI;
- no required audio;
- wired Ethernet first;
- IPv4 + IPv6;
- cgroup v2;
- namespaces;
- seccomp;
- OverlayFS;
- nftables;
- rfkill support compiled in;
- JETOS hardware service;
- JETOS network service;
- a transitional boot/init path until the Python supervisor is proven reliable.

After that works, repeat the same JETOS API on ARM64.

This sequence tests the JETOS architecture without mixing it immediately with the much harder problem of reverse-engineering or supporting a random mobile device.

---

## 27. Open decisions

The following are intentionally unresolved and may be added, removed, or changed later:

- exact init/bootstrap implementation;
- glibc vs musl;
- exact compiler/toolchain;
- exact kernel branch/update cadence;
- whether Portage remains installed on production devices;
- whether runtime upgrades are package-based or atomic-image-based;
- exact application package/container format;
- exact LSM/hardening choice;
- exact TLS implementation;
- exact graphics API;
- exact graphics backend;
- exact audio API;
- exact audio backend;
- exact input API;
- exact permissions/capability schema;
- exact device selected for first ARM64/mobile test;
- whether JETOS eventually replaces ebuilds with a Python-native package recipe format.

---

## 28. Research basis

Primary references consulted for this version:

- Gentoo Handbook / About — Portage is written in Python and Gentoo is designed around source-based customization:
  https://wiki.gentoo.org/wiki/Handbook:Parts/Installation/About
- Gentoo Portage repository — Portage license and native-extension information:
  https://github.com/gentoo/portage
- Gentoo profiles — profiles define system packages, USE defaults, package versions, and architecture defaults:
  https://wiki.gentoo.org/wiki/Profile
- Gentoo Handbook — architecture overview including ARM/ARM64:
  https://wiki.gentoo.org/wiki/Handbook:Main_Page/en
- Gentoo kernel handbook — firmware requirements:
  https://wiki.gentoo.org/wiki/Handbook:AMD64/Installation/Kernel/en
- Linux kernel device model:
  https://www.kernel.org/doc/html/latest/driver-api/driver-model/overview.html
- Linux ACPI device enumeration:
  https://docs.kernel.org/firmware-guide/acpi/enumeration.html
- Linux rfkill:
  https://docs.kernel.org/driver-api/rfkill.html
- Docker Engine security / namespaces and cgroups:
  https://docs.docker.com/engine/security/
- Docker cgroup v2 notes:
  https://docs.docker.com/engine/containers/runmetrics/
- Docker Engine binary prerequisites:
  https://docs.docker.com/engine/install/binaries/
- Buildroot manual:
  https://buildroot.org/downloads/manual/manual.html
- Gentoo Development Guide — license metadata:
  https://devmanual.gentoo.org/general-concepts/licenses/
- Gentoo Development Guide — copyright/license policy:
  https://devmanual.gentoo.org/general-concepts/copyright-policy/

---

## 29. Change rule

This is a living document.

Any requirement may be:

- added;
- deleted;
- rewritten;
- promoted from SHOULD to MUST;
- demoted from MUST to SHOULD;
- marked experimental;
- deferred.

When a requirement changes, keep its ID whenever it still represents the same underlying requirement. Add new IDs for materially new requirements.
---

# JETOS Requirements Addendum — v0.2

**Revision date:** 2026-10-03  
**Status:** Canonical additions to the JETOS bootstrap philosophy.

## 30. Core philosophy: introspection before convenience

### JETOS-REQ-150 — The shipped operating system is enumerable

Every normal JETOS build MUST be able to produce a machine-readable manifest of every file that is part of the operating-system image.

For every shipped file where meaningful, the manifest SHOULD include:

- absolute installed path;
- file type;
- size;
- cryptographic hash;
- owning JETOS component/package;
- upstream project and version when imported;
- source/build provenance;
- applicable license information;
- architecture;
- whether the file is JETOS-owned or imported substrate;
- whether it is executable code, configuration, firmware, data, documentation, or generated output.

The goal is that JETOS can answer:

> What exactly is on this machine, why is it here, where did it come from, and what created it?

### JETOS-REQ-151 — Build graph is inspectable

The JETOS build MUST preserve enough metadata to reconstruct the relationship between:

`source -> build rule -> generated artifact -> installed file -> image`

A developer should be able to ask why a file exists and trace it back to the source and rule that placed it there.

### JETOS-REQ-152 — Runtime introspection surface

JETOS SHOULD eventually expose first-class commands/APIs conceptually equivalent to:

```text
jetos inspect files
jetos inspect file <path>
jetos inspect components
jetos inspect source
jetos inspect languages
jetos inspect exceptions
jetos inspect hardware
jetos inspect capabilities
jetos inspect kernel
jetos inspect network
jetos inspect build
```

The exact command names are not frozen.

The important requirement is that introspection is a designed operating-system feature rather than an afterthought.

---

## 31. JETOS source-language constitution

### JETOS-REQ-160 — Python is the default programming language

A new JETOS-owned file that contains executable program logic MUST be Python unless an approved exception applies.

This applies to:

- operating-system services;
- build tooling;
- developer tooling;
- test runners;
- installers;
- image-construction logic;
- system-management commands;
- Git hooks owned by JETOS;
- package/build orchestration owned by JETOS;
- code generators owned by JETOS.

A build tool being "only a script" does not exempt it from this rule.

### JETOS-REQ-161 — C is the first native exception

C MAY be used when Python cannot reasonably or correctly implement the required boundary.

Examples include:

- CPython extension modules;
- system-call or ABI shims not adequately exposed by Python;
- extremely early bootstrap code before Python is available;
- hardware/register access where a native layer is required;
- performance-critical primitives proven by measurement to need native implementation;
- interoperability with required native APIs.

C is an exception language, not an equal default.

### JETOS-REQ-162 — Assembly is a registered low-level exception

Assembly MAY be used when the required operation cannot reasonably be implemented in Python or C.

Every JETOS-owned assembly source file MUST be explicitly listed in the exception registry with:

- path;
- target architecture;
- purpose;
- reason C is insufficient;
- owner/component;
- review status.

Assembly is expected to remain rare and architecture-specific.

### JETOS-REQ-163 — No accidental language expansion

No additional executable programming language becomes part of JETOS merely because an imported tool happens to support it.

Adding another JETOS-owned implementation language requires an explicit architectural decision and an update to this document.

Examples that are **not** automatically approved for JETOS-owned executable source:

- shell;
- Perl;
- Ruby;
- JavaScript/TypeScript;
- Rust;
- Go;
- Lua;
- C++;
- Java;
- awk as a programming layer.

Imported upstream projects may contain any language required by those projects. Their presence must be visible through provenance metadata and does not make that language part of the JETOS-owned programming model.

### JETOS-REQ-164 — Declarative formats are allowed

Declarative formats are not treated as programming-language violations when they are being used as data/configuration rather than as a hidden general-purpose programming environment.

Examples that MAY be used where appropriate:

- TOML;
- JSON;
- YAML when justified;
- INI-style configuration;
- kernel `.config`;
- Device Tree source/data required by Linux tooling;
- system metadata;
- package metadata;
- protocol schemas;
- static tables;
- documentation formats.

Preference order for new JETOS-owned declarative data:

1. TOML where human editing matters;
2. JSON where strict machine interchange matters;
3. purpose-specific standardized formats when required.

A declarative language that grows substantial control flow SHOULD trigger review: the logic may belong in Python instead.

### JETOS-REQ-165 — Exception registry

JETOS MUST maintain an authoritative machine-readable registry of every JETOS-owned non-Python executable-source exception.

Conceptual record:

```toml
[[exception]]
path = "python_extensions/example/example.c"
language = "C"
component = "example"
reason = "CPython ABI boundary"
python_alternative = "insufficient for required ABI"
architecture = "all"
status = "approved"
```

The exact schema is not frozen.

### JETOS-REQ-166 — Language gate

The repository SHOULD contain an automated language-policy check that:

1. inventories source files;
2. classifies programming language;
3. allows Python;
4. allows approved declarative formats;
5. allows C/assembly only when registered;
6. identifies imported/vendor source separately;
7. rejects unexplained JETOS-owned executable source.

This check SHOULD run:

- locally before commit;
- in the central repository before accepting protected-branch updates;
- during image construction.

---

## 32. Imported Gentoo and Linux code are visible exceptions, not hidden exceptions

### JETOS-REQ-170 — Imported substrate is explicitly distinguished

The initial JETOS tree may necessarily contain upstream code written in languages outside the JETOS-owned language rule.

Examples include:

- Linux kernel C and assembly;
- Gentoo ebuild Bash;
- GNU toolchain implementation languages;
- CPython C;
- bootloader source;
- firmware;
- imported libraries and applications.

These files MUST be classified as imported substrate/vendor/upstream source.

They MUST NOT be silently counted as if JETOS authored them.

### JETOS-REQ-171 — Upstream replacement program

JETOS may progressively replace imported control-plane components with JETOS-owned Python implementations.

Replacement priorities SHOULD favor code that improves:

- inspectability;
- reliability;
- comprehensibility;
- portability;
- boot simplicity;
- security;
- removal of unnecessary runtime dependencies.

Rewriting upstream code merely to satisfy a language aesthetic is not by itself sufficient reason to replace mature, security-sensitive, hardware-critical substrate.

### JETOS-REQ-172 — Gentoo remains modifiable

JETOS should retain enough of the Gentoo source/build environment on the development side that JETOS developers can:

- patch Gentoo packages;
- alter ebuild behavior;
- maintain a JETOS profile/overlay;
- replace packages;
- submit improvements upstream when appropriate;
- reproduce JETOS builds from source.

JETOS is not constrained to consume Gentoo as an immutable binary vendor.

---

## 33. Development side versus deployed side

### JETOS-REQ-180 — Source-oriented development system

The JETOS development environment is expected to retain:

- Gentoo source/package metadata;
- compilers and linkers;
- Python development environment;
- headers;
- kernel sources/configuration;
- image builders;
- test harnesses;
- package-build capability;
- device build profiles;
- provenance tooling;
- license tooling.

The development environment may be comparatively large.

### JETOS-REQ-181 — Deployed system is capability-minimal

A deployed JETOS image SHOULD contain only the components needed by that device and its intended role.

Examples:

- no audio stack if the supported device has no useful audio hardware and no required audio role;
- no graphical user environment if there is no display or no graphical role;
- no Bluetooth stack if the device has no Bluetooth or the device profile disables it;
- no Wi-Fi stack if the target has no Wi-Fi and does not need it;
- no compiler merely because the development system used one.

### JETOS-REQ-182 — Capability presence does not imply capability activation

Hardware discovery and software inclusion are separate policy stages.

A target may have speakers but intentionally ship without an audio role.

A target may have Wi-Fi but intentionally ship with radio/network capability disabled.

JETOS must be able to say:

- capability exists;
- implementation is installed;
- capability is permitted;
- capability is active.

These are different states.

---

## 34. GUI, graphics, and audio are optional bootstrapped capabilities

### JETOS-REQ-190 — GUI is optional, not forbidden

JETOS does **not** have a universal "no GUI" rule.

Instead:

- a headless target may omit graphical user-interface components;
- a target with a display may bootstrap the minimum graphics/input stack needed by that device or role;
- a graphical application may request graphics capabilities through JETOS APIs;
- graphics are not installed merely because conventional desktop Linux would install them.

### JETOS-REQ-191 — Audio is optional, not forbidden

JETOS does **not** have a universal "no audio" rule.

A device profile may bootstrap audio support when:

- appropriate audio hardware exists; and
- the device role requires it.

If a device has no useful audio hardware, the JETOS image should normally omit the audio implementation.

### JETOS-REQ-192 — Bootstrap what the device actually needs

The image builder should derive its software composition from:

1. architecture;
2. device profile;
3. detected/declared hardware capabilities;
4. intended device role;
5. explicit JETOS policy.

The long-term goal is not "install every possible stack and disable what is unused."

The goal is:

> know what the machine is capable of, then build or activate only what the machine is intended to use.

### JETOS-REQ-193 — Backend versus public API

JETOS may use existing Linux graphics/audio/input backends where practical.

Applications should target stable JETOS APIs rather than depending directly on whatever backend is selected for one device.

This permits:

- no backend on a headless device;
- one backend on x86-64 PC hardware;
- a different backend on an ARM64 tablet;
- future replacement of a backend without rewriting every JETOS application.

---

## 35. Architecture terminology and support

### JETOS-REQ-200 — Use instruction-set names in JETOS design language

JETOS documentation SHOULD prefer:

- **x86-64** for the 64-bit x86 instruction-set family;
- **AArch64 / ARM64** for the 64-bit Arm instruction-set family.

"AMD64" may appear where an upstream project, ABI, package manager, compiler, or platform specifically uses that term.

JETOS should not treat one vendor's label as the conceptual name of the architecture.

### JETOS-REQ-201 — Same JETOS architecture, architecture-specific builds

JETOS aims to support at least both:

- x86-64;
- AArch64.

This does not mean one binary image contains identical executable machine code for both architectures.

The intended model is:

- same JETOS source architecture;
- same public APIs;
- same behavioral test suite;
- separate native builds for each ISA;
- architecture-specific C/assembly only where required;
- architecture-specific kernel/device support where required.

### JETOS-REQ-202 — Do not hide architecture differences

Where x86-64 and AArch64 require different:

- boot mechanisms;
- memory-order assumptions;
- assembly;
- interrupt/firmware interfaces;
- device-tree/ACPI handling;
- SIMD implementations;
- kernel configuration;

those differences should be isolated and documented rather than disguised.

---

## 36. Repository philosophy

### JETOS-REQ-210 — Git hosting is replaceable infrastructure

JETOS MUST NOT architect itself around GitHub-specific behavior.

The authoritative repository may be:

- a local bare Git repository;
- a self-hosted Git service;
- GitHub;
- another Git-compatible remote.

Repository history should remain ordinary Git and portable between hosts.

### JETOS-REQ-211 — Bare-repository operation is a first-class option

JETOS SHOULD be maintainable with a conventional bare Git repository and ordinary Git transport.

Central policy enforcement should therefore be implementable using normal Git server hooks rather than requiring proprietary hosting features.

### JETOS-REQ-212 — Hooks follow the JETOS language rule

JETOS-owned Git hooks containing program logic SHOULD be Python executables.

Useful future hooks include:

**pre-commit**
- language-policy scan;
- exception-registry validation;
- generated-manifest freshness check;
- formatting/static checks;
- accidental secret detection;
- prohibited generated/binary-file check where applicable.

**commit-msg**
- optional commit-format validation;
- provenance/change-ticket annotations if JETOS later adopts them.

**pre-receive / update on the authoritative bare repo**
- authoritative language-policy enforcement;
- reject unregistered native-source exceptions;
- prevent direct mutation of protected refs;
- validate required metadata;
- prevent history that drops mandatory provenance/license records.

Hooks are defense-in-depth. The build system itself must repeat critical validation rather than trusting client-side hooks.

### JETOS-REQ-213 — Repository can describe itself

The source tree SHOULD be able to generate a repository report including:

- JETOS-owned Python lines/files;
- approved C exceptions;
- approved assembly exceptions;
- declarative files;
- imported upstream source by project/language;
- generated artifacts;
- licenses;
- unclassified files.

Unclassified files should be treated as a build/policy failure.

---

## 37. Testing hardware philosophy

### JETOS-REQ-220 — Real devices are part of the operating-system test matrix

JETOS should have inexpensive sacrificial/replaceable test hardware rather than depending only on VMs or on difficult-to-unlock personal devices.

The project SHOULD maintain explicit categories:

- VM targets for fast architecture/testing;
- generic x86-64 test machines;
- AArch64 development boards;
- later, selected phone/tablet-class devices with known boot support;
- networking-off verification hardware where useful.

### JETOS-REQ-221 — Do not require modifying valuable locked-down personal hardware

JETOS development does not require jailbreaking or modifying personal Apple devices.

If Apple hardware is ever supported, it should be through a deliberately chosen and documented Linux-support path on hardware the project is willing to use for operating-system development.

### JETOS-REQ-222 — Hardware acceptance records

Each physical test device SHOULD have a record containing:

- model;
- CPU architecture;
- boot method;
- storage;
- RAM;
- network hardware;
- display/input/audio capabilities;
- required firmware;
- known unsupported components;
- JETOS build revision last tested;
- automated test results;
- recovery procedure.

---

## 38. System tests become part of the definition of JETOS

### JETOS-REQ-230 — Cross-architecture behavioral parity

Where a feature is advertised on both x86-64 and AArch64, the same behavior-level tests SHOULD pass on both.

### JETOS-REQ-231 — Minimal image assertions

Every target image SHOULD have tests that assert both presence and absence.

Examples:

- Python is present.
- Required filesystem support is present.
- Required network stack is present.
- GUI stack is absent on a headless target.
- Audio implementation is absent when not requested.
- Bluetooth is absent when not requested.
- Compiler is absent on a production runtime image unless explicitly requested.
- every executable-source exception is registered.
- every installed file is classified.

### JETOS-REQ-232 — Introspection is tested

A build is invalid if its manifest/introspection metadata cannot account for the shipped image.

The manifest must therefore be checked against the actual generated root filesystem/image, not merely generated optimistically from package declarations.

---

## 39. Revised guiding statements

The following statements summarize the JETOS philosophy at v0.2.

### 39.1 Source rule

> If JETOS owns executable logic, write it in Python.  
> If Python cannot correctly do the job, use a documented C boundary.  
> If C cannot correctly do the job, use a documented architecture-specific assembly boundary.  
> If an exception exists, JETOS must be able to show it to us.

### 39.2 Introspection rule

> No mysterious files. No mysterious build steps. No mysterious languages.

### 39.3 Device rule

> Do not install a generic desktop computer onto every piece of hardware. Discover the device, declare its role, and bootstrap the capabilities it actually needs.

### 39.4 Portability rule

> One JETOS design and API; native implementations for each supported instruction-set architecture.

### 39.5 Gentoo rule

> Gentoo is source material, build infrastructure, and an upstream we are allowed to understand and improve—not a black box and not a binary base image.

### 39.6 Repository rule

> Git is the history format. Hosting is optional infrastructure.

---

## 40. New near-term design work

Before attempting a real JETOS image, define these artifacts:

1. `PHILOSOPHY.md`
2. `LANGUAGE_POLICY.toml`
3. `EXCEPTIONS.toml`
4. `FILE_MANIFEST.schema.json` or an equivalent schema
5. `DEVICE_PROFILE.schema.json` or an equivalent schema
6. Python source-language scanner
7. Python build/provenance manifest generator
8. Python Git hook entry points
9. first x86-64 test-device profile
10. first AArch64 test-device profile
11. first VM profile
12. system-test specification for boot, Python, storage, network ON/OFF, container primitives, and introspection

Implementation can follow after these rules are stable enough to prevent the bootstrap repository from growing accidental complexity.

---

## 41. Dona Code and Unicode text model

### JETOS-REQ-240 — Dona Code is the JETOS character encoding model

JETOS uses the **Dona Code character encoding system** for its project-level text architecture.

Dona Code MUST interoperate with Unicode.

Until a more specific Dona Code byte-level specification is defined, Unicode scalar values are the semantic text model and UTF-8 is the canonical JETOS-controlled byte representation.

### JETOS-REQ-241 — UTF-8 is the normal JETOS encoding

JETOS-owned textual files, APIs, manifests, logs, configuration, protocols, and source files SHOULD use UTF-8 unless an external interoperability boundary requires another encoding.

Legacy locale-dependent encodings MUST NOT silently determine core JETOS behavior.

### JETOS-REQ-242 — Python text and binary data are distinct

JETOS-owned Python code SHOULD use `str` for Unicode text and `bytes` for raw binary data.

Encoding and decoding MUST occur explicitly at boundaries.

### JETOS-REQ-243 — JETOS C text APIs use UTF-8

JETOS-owned C interfaces carrying text SHOULD use UTF-8 and SHOULD prefer explicit byte lengths where practical.

Ownership, validation state, embedded-NUL policy, and normalization requirements must be documented for each interface.

### JETOS-REQ-244 — Full Unicode coverage

JETOS text handling MUST support the full Unicode scalar-value range rather than assuming ASCII.

The system test suite SHOULD include multilingual text, combining marks, right-to-left text, CJK, emoji, supplementary-plane characters, variation selectors, and zero-width characters.

### JETOS-REQ-245 — Imported arbitrary bytes must round-trip

JETOS MUST NOT assume that every pre-existing Linux/POSIX filename is valid UTF-8.

JETOS-created filenames SHOULD be valid UTF-8, but arbitrary imported filename bytes must remain representable and round-trippable through a raw-path or reversible compatibility mechanism.

Malformed UTF-8 MUST NOT be silently replaced and written back as different data.

### JETOS-REQ-246 — Normalization is explicit

JETOS MUST NOT silently normalize arbitrary Unicode text.

NFC or another normalization form may be required for a specific identifier/protocol, but that requirement must be explicit.

Exact filenames, hashes, provenance records, and binary identity MUST preserve their defined byte representation.

### JETOS-REQ-247 — Foreign encodings are compatibility boundaries

UTF-16, UTF-32, legacy code pages, and other encodings may be accepted where external systems require them, but conversion to and from the JETOS Unicode/UTF-8 model must be explicit and testable.

### JETOS-REQ-248 — Unicode must remain inspectable

JETOS inspection/developer tools SHOULD make potentially deceptive Unicode features visible, including bidirectional controls, invisible characters, mixed scripts, confusables, and normalization differences.

Support for these characters does not imply hiding their presence.

### JETOS-REQ-249 — Encoding behavior is tested

JETOS system tests SHOULD cover Unicode encode/decode round trips, Python/C UTF-8 boundaries, multilingual CLI and filesystem cases, invalid UTF-8 rejection, raw filename-byte round trips, and normalization preservation.

The detailed policy is maintained in `docs/architecture/TEXT_ENCODING.md`.
