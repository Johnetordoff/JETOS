# GCC ordered_hash_map -> C experiment

This is the first JETOS C++-elimination proof of concept.

It does **not** claim to replace GCC's `ordered_hash_map` in GCC yet. It is a readable C implementation of the behaviors exercised by GCC's existing `ordered-hash-map-tests.cc`, pinned to the upstream revision in `UPSTREAM.toml`.

The upstream tests cover:

- string-pointer keys to integer values;
- integer keys to string-pointer values;
- insertion-order iteration;
- removal and reinsertion;
- copy independence.

The C test file deliberately mirrors those behavioral cases. The local JETOS test runner compiles it as strict C11 with warnings-as-errors and then repeats the run under AddressSanitizer + UndefinedBehaviorSanitizer.

## Why this is not yet an upstream GCC replacement

GCC's implementation is a C++ template layered on GCC's `hash_map` and `auto_vec` internals. Replacing it inside GCC requires converting call sites and integrating a C ABI/type-specialization strategy. This experiment validates the translation discipline before that larger integration.
