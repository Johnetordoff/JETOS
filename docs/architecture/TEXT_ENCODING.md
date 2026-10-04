# JETOS Dona Code / Unicode Text Model

**Status:** Architecture rule  
**Date:** 2026-10-03

## 1. Canonical rule

JETOS uses the **Dona Code character encoding system** as its project-level text model.

Dona Code MUST interoperate with Unicode.

Until a more specific Dona Code byte-level specification is defined, JETOS uses **Unicode scalar values as the semantic text model** and **UTF-8 as the canonical byte encoding whenever JETOS controls the representation**.

This means:

- Python `str` is the normal JETOS representation of text.
- UTF-8 is the normal encoded representation for files, protocols, manifests, logs, configuration, and C-facing text.
- Raw binary data remains `bytes` and is never implicitly treated as text.
- Foreign encodings are converted at explicit compatibility boundaries.

Dona Code is a JETOS project term. It should not be assumed to mean an unrelated external protocol or standard merely because it has a similar name.

## 2. Unicode coverage

JETOS text APIs MUST support the full Unicode scalar-value range.

Tests should include at least:

- ASCII;
- Latin characters with diacritics;
- Greek;
- Cyrillic;
- Arabic and right-to-left text;
- Hebrew;
- Devanagari;
- CJK characters;
- combining marks;
- emoji;
- supplementary-plane characters;
- variation selectors;
- zero-width characters;
- mixed-script strings.

A feature that works only for ASCII is not a complete JETOS text implementation unless explicitly documented as an ASCII-only protocol boundary.

## 3. UTF-8 is the canonical JETOS byte encoding

When JETOS owns the format, text SHOULD be encoded as UTF-8.

Examples include:

- JETOS configuration files;
- manifests;
- package metadata;
- provenance records;
- logs;
- command output;
- service protocols;
- IPC text payloads;
- source files;
- documentation;
- filenames created by JETOS where the backing filesystem permits them.

UTF-8 SHOULD be used without a byte-order mark unless a specific external format requires one.

## 4. Python boundary

JETOS-owned Python code SHOULD:

- use `str` for human text;
- use `bytes` for uninterpreted binary data;
- encode/decode explicitly at I/O boundaries;
- default to UTF-8 for JETOS-owned text formats;
- avoid locale-dependent implicit encodings.

Core JETOS behavior MUST NOT depend on a legacy system locale such as ISO-8859-1 or Windows code pages.

## 5. C boundary

JETOS C APIs carrying text SHOULD use UTF-8.

A preferred interface is an explicit pointer plus byte length rather than relying everywhere on NUL-terminated strings:

```c
typedef struct {
    const char *data;
    size_t byte_length;
} jetos_utf8_view;
```

The API contract MUST say whether:

- the bytes have already been UTF-8 validated;
- embedded NUL is permitted;
- ownership is borrowed or transferred;
- normalization is required;
- malformed input is rejected or passed through as raw bytes.

## 6. Filesystem compatibility

Linux/POSIX filenames are fundamentally byte sequences with a few reserved byte values. They are not guaranteed to be valid UTF-8.

Therefore:

- filenames created by JETOS SHOULD be valid UTF-8;
- the normal JETOS filesystem API SHOULD expose valid text as Unicode;
- imported or pre-existing non-UTF-8 filenames MUST remain round-trippable;
- JETOS MUST NOT silently replace invalid bytes with U+FFFD and then write back a different filename;
- raw-path APIs or a reversible escape strategy MUST remain available for compatibility.

Display software may visibly escape invalid byte sequences rather than pretending they are Unicode text.

## 7. Normalization

JETOS MUST distinguish encoding from normalization.

UTF-8 encoding does not imply NFC, NFD, NFKC, or NFKD normalization.

Default policy:

- preserve the original Unicode sequence;
- do not silently normalize arbitrary user data;
- allow NFC normalization where a particular identifier or protocol explicitly requires canonical comparison;
- never normalize bytes used for cryptographic hashes, provenance verification, exact filenames, or binary identity unless the relevant specification explicitly says to.

## 8. Invalid text

Malformed UTF-8 MUST NOT be silently accepted as valid JETOS text.

At a text boundary, JETOS should either:

1. reject malformed input with an explicit error; or
2. preserve it through a documented reversible byte-preserving compatibility representation.

Lossy replacement is allowed only when explicitly requested for display or recovery.

## 9. Foreign encoding boundaries

JETOS may encounter UTF-16, UTF-32, legacy code pages, Shift-JIS, ISO-8859 variants, or other encodings through files, protocols, firmware, APIs, or applications.

Those encodings are compatibility inputs, not the canonical JETOS representation.

The boundary SHOULD:

1. know or determine the external encoding;
2. decode it explicitly;
3. convert to JETOS Unicode text;
4. retain original bytes when lossless round-tripping matters;
5. encode back explicitly when communicating with the foreign interface.

## 10. Locale

JETOS SHOULD separate **language/locale** from **character encoding**.

The system may support many languages and locale conventions while retaining UTF-8 as the normal encoding.

A minimal JETOS environment SHOULD prefer a UTF-8-capable locale such as `C.UTF-8` or a JETOS equivalent rather than allowing core behavior to vary with legacy locale encodings.

## 11. Security and inspectability

Unicode support must not make source or system metadata deceptive.

JETOS tools SHOULD be able to identify or visibly annotate:

- bidirectional control characters;
- invisible or zero-width characters;
- mixed-script identifiers;
- confusable characters;
- non-normalized equivalent forms where relevant.

These characters remain valid Unicode; the requirement is visibility, not a blanket ban.

Source/provenance inspection should make hidden text effects apparent.

## 12. Source-code policy

JETOS source files SHOULD be UTF-8.

Python source is UTF-8.

JETOS C source SHOULD also be stored as UTF-8, while identifiers and literals should remain understandable during review.

Generated source MUST preserve valid UTF-8 and deterministic byte output.

## 13. Protocol and manifest rule

Every JETOS-owned textual serialization SHOULD declare or normatively define UTF-8 rather than relying on environment defaults.

If a format is binary but contains textual fields, those fields SHOULD be explicitly specified as UTF-8 unless another encoding is required for interoperability.

## 14. Testing

JETOS text tests SHOULD verify:

- encode/decode round trips;
- non-ASCII file and directory names;
- multilingual environment variables and process arguments where the platform permits them;
- Unicode command-line input/output;
- Python-to-C UTF-8 handoff;
- invalid UTF-8 rejection;
- arbitrary-byte filename round-trip;
- normalization preservation;
- supplementary-plane characters;
- bidirectional and combining-character display diagnostics.

## 15. Canonical shorthand

> Dona Code is Unicode-capable.  
> Unicode is the text model.  
> UTF-8 is the normal JETOS byte encoding.  
> Raw bytes remain raw bytes.  
> Never silently destroy information at an encoding boundary.
