# JETOS Philosophy

**Version:** 0.2  
**Date:** 2026-10-03

JETOS is an operating-system project built around **inspectability, capability-driven composition, and a Python-first control plane**.

## The machine should explain itself

A JETOS system should be able to account for what is on it.

We should be able to enumerate every shipped operating-system file and answer:

- What is this file?
- Why is it installed?
- What component owns it?
- Is it JETOS code or imported upstream code?
- What source created it?
- What language is that source written in?
- What license applies?
- What build rule produced it?
- What hardware or system capability requires it?

Unknown or unclassified operating-system files are defects.

## Python first

New JETOS-owned executable logic is Python by default.

That includes system services, image builders, build tools, developer tools, tests, package orchestration, repository hooks, and administrative commands.

When Python cannot correctly implement a required boundary, C is permitted as a documented exception.

When C cannot correctly implement the operation, architecture-specific assembly is permitted as a documented exception.

Every exception must be visible in an authoritative registry.

Imported upstream components are not forced into this rule retroactively. Linux, CPython, bootloaders, firmware, Gentoo packages, and other substrate may contain the languages their upstream projects require. JETOS must identify those files as imported rather than pretending they are JETOS-authored code.

Declarative formats are allowed when they are genuinely being used as data or configuration. Control flow belongs in Python unless there is a compelling reason otherwise.

## Gentoo is a bootstrap source ecosystem

JETOS is not intended to be a renamed binary Gentoo installation.

Gentoo gives JETOS a source-oriented ecosystem, Portage, profiles, package recipes, architecture support, and an upstream we can patch and understand.

The JETOS development side may remain deeply Gentoo-capable so that we can modify packages, kernels, profiles, and builds.

The deployed side should contain only what its target needs.

Over time, JETOS may replace Gentoo control-plane components with Python-native equivalents. It does not need to rewrite mature low-level substrate merely to make a language-count statistic look cleaner.

## Build for capabilities, not for the stereotype of a computer

A machine is not automatically a "desktop."

JETOS should discover or declare capabilities such as:

- display;
- touch;
- keyboard;
- pointer;
- speakers;
- microphone;
- camera;
- Ethernet;
- Wi-Fi;
- Bluetooth;
- cellular;
- battery;
- sensors;
- GPU;
- storage;
- virtualization.

Then the device profile and intended role determine what is bootstrapped.

A headless target does not need a GUI.

A target without an audio role does not need an audio stack.

A tablet with a display and speakers may need both.

Having hardware does not automatically mean JETOS must enable it.

## One JETOS, multiple native instruction sets

JETOS should target at least x86-64 and AArch64.

The goal is not one identical machine-code image.

The goal is:

- one JETOS architecture;
- one public API model;
- one behavior-level test suite;
- native builds for each instruction-set architecture;
- isolated architecture-specific native code where unavoidable.

Architecture differences should be documented, not concealed.

## Networking is a capability with a master boundary

JETOS owns the user-visible networking policy.

A single master OFF state must prevent external network communication across ordinary interfaces and containers, and disable controllable radios where the device allows it.

JETOS must report the strength of that guarantee rather than claiming a hardware radio state it cannot verify.

## Graphics and audio are JETOS capabilities, not universal baggage

JETOS does not have a permanent "no graphics" or "no audio" rule.

It has a rule against installing layers merely because a conventional distribution normally does.

If the device and role need graphics or audio, JETOS bootstraps the required backend and exposes it through JETOS APIs.

If they do not, omit it.

## Development and deployment are different systems

The development environment can be large.

It may contain:

- Gentoo;
- kernel source;
- compilers;
- linkers;
- Portage;
- headers;
- build tools;
- debuggers;
- provenance tooling.

A deployed image should be small and deliberate.

The project must test both what a target contains and what it successfully omits.

## Git is the repository model; hosting is replaceable

JETOS must not depend on GitHub.

A bare Git repository is a valid authoritative source repository.

JETOS-owned repository hooks should themselves be Python and should enforce important rules such as language policy, provenance metadata, and exception registration.

Client hooks are useful convenience. Server-side validation and build-time validation are authoritative.

## Test on real, replaceable hardware

Virtual machines are essential but insufficient.

JETOS should maintain inexpensive real test devices for x86-64 and AArch64 and later add selected phone/tablet-class hardware with documented Linux boot support.

The project should not depend on jailbreaking valuable personal devices merely to prove its architecture.

## Guiding shorthand

> No mysterious files.  
> No mysterious build steps.  
> No mysterious languages.

> If JETOS owns executable logic, Python first.  
> C when Python cannot do it correctly.  
> Assembly when C cannot do it correctly.  
> Every exception documented.

> Discover the machine.  
> Declare its role.  
> Bootstrap only what it needs.

> Gentoo is upstream source infrastructure, not JETOS's identity.

> Git is history. Hosting is optional.
