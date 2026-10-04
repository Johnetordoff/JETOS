# Test results

Test date: 2026-10-03

Upstream reference:
- GCC commit: `4bf11aca586c9eef753b6f76d29ae19e1b505694`
- `gcc/ordered-hash-map.h` blob: `3331394d985820d10ad2150a1c35ceec8f13985b`
- `gcc/ordered-hash-map-tests.cc` blob: `b033bc5b7c2c7013cd5b54fd0eef3bb43b85ad16`

Local toolchain:
- GCC 14.2.0
- Python 3.13.5
- host architecture: x86_64

Results:

```text
strict C11 / -Wall -Wextra -Werror -pedantic / -O2:
ordered_hash_map C port: 91 checks passed

AddressSanitizer + UndefinedBehaviorSanitizer:
ordered_hash_map C port: 91 checks passed

JETOS repository test suite: PASS
```

## Scope

The behavioral cases are adapted from GCC's existing `ordered-hash-map-tests.cc`: insertion/retrieval, insertion order, removal/reinsertion, and copy independence.

This does **not** yet mean GCC itself has been rebuilt with the C implementation. GCC's integrated `-fself-test` suite requires a configured GCC build tree and conversion of C++ call sites/template uses. The next integration stage is to replace one actual GCC specialization/call path and run GCC's native selftest target in a full build environment.
