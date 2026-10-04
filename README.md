# JETOS — John E Tordoff's Operating System

JETOS is a Python-first operating-system project bootstrapped from Gentoo/Linux source ecosystems.

Current repository phase: architecture + migration experiments.

Language direction:
- Python for JETOS-owned control logic.
- C for native substrate and ports.
- Assembly only for explicitly registered architecture-specific irreducibles.
- C++ is migration debt.
- Bash may exist as a shell or in quarantined package-build environments, but not as the JETOS control language.

Text direction:
- Dona Code is the JETOS character-encoding model.
- Unicode is supported across JETOS text APIs.
- UTF-8 is the canonical encoding when JETOS controls the byte representation.
- Raw byte data remains explicitly representable at compatibility boundaries.

See `PHILOSOPHY.md`, `REQUIREMENTS.md`, and `docs/architecture/`.


## Docker test image

JETOS currently has a Docker-based userspace/test image. Docker supplies the Linux kernel; this is **not yet a standalone bootable JETOS kernel image**.

Build it:

```bash
git clone https://github.com/Johnetordoff/JETOS.git
cd JETOS
docker build -t jetos:dev .
```

The build runs both:

```bash
python tools/test.py
python tools/test_unicode.py
```

A successful build therefore verifies the current C port and the Dona Code / Unicode smoke tests.

Open an interactive JETOS test shell:

```bash
docker run --rm -it jetos:dev
```

Inside the container, rerun tests with:

```bash
python tools/test.py
python tools/test_unicode.py
```

You can also test Unicode directly:

```bash
python - <<'PY'
text = "JETOS: café Ελληνικά العربية 漢字 🧪🚀"
raw = text.encode("utf-8")
print(text)
print(raw)
print(raw.decode("utf-8"))
assert raw.decode("utf-8") == text
PY
```

The image sets `LANG=C.UTF-8` and `LC_ALL=C.UTF-8`.
