# Shared native source

`source/shared/` is reserved for native source whose responsibility is genuinely shared by the Linux-side and CPython-derived JetLang-side portions of the integrated JetOS runtime.

Code belongs here only when the ownership is truly shared rather than duplicated for convenience. Changes must satisfy the integrated-runtime qualification rules in `MANDATE.md` and `ARCHITECTURE.md`.
