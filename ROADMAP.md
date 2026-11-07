# Specification completeness -- and the roadmap it implies

This is the project's north star: every protocol obligation bmpkit could plausibly take on,
with an honest status against the code at `HEAD`. It is blunt about gaps on purpose. A
roadmap that overstates its coverage is not a plan, it is marketing.

**The honesty rule:** a row may read `[ok]` only when a named test would fail if the
behaviour regressed. Reading the code and agreeing with it is not enough. That is how
"decoded but never sent" quietly becomes "implemented".

Legend: `[ok]` implemented and pinned by a named test -- `[part]` partial, with what is
missing stated -- `[ ]` not implemented -- `[no]` deliberate non-goal.

A Where cell marked `(to be written)` names the test that will pin the row once it exists; no
such test has been written yet, and the row cannot leave `[ ]` until it has. The Milestone
column places the row on the ladder in section 2, and `-` means it is not placed yet.

Update the affected row in the same commit that changes the behaviour. A row and its test
drift apart within one release, and the document becomes useless exactly when it is needed.

## 1. Obligations

| Obligation | Spec | Status | Where | Milestone |
|---|---|---|---|---|
| `header.decode_common()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::test_decode_common` (to be written) | M1 |
| `messages.decode_route_monitoring()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::test_decode_route_monitoring` (to be written) | M1 |
| `messages.decode_statistics()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::test_decode_statistics` (to be written) | M4 |
| `rib.view_of()` | RFC 8671, RFC 9069 | `[ ]` | `tests/test_obligations.py::test_view_of` (to be written) | M3 |
| `server.serve()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::test_serve` (to be written) | M2 |
| `mirror.extract_bgp_message()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::test_extract_bgp_message` (to be written) | M4 |
| `replay.from_capture()` | design | `[ ]` | `tests/test_obligations.py::test_from_capture` (to be written) | M5 |

## 2. Milestones

- M1 header and message codec with vectors from a live FRR or BIRD speaker
- M2 the collector server with per peer state and bounded buffers
- M3 view selection for Adj-RIB-In, Adj-RIB-Out and Loc-RIB
- M4 statistics, termination reasons and the mirroring passthrough
- M5 capture and replay tooling wired into the test suite
- M6 publication: 0.1.0 with a mirrored RIB comparison against a router CLI

Every milestone is accepted by its rows above flipping to `[ok]` with a named test, not by
the code existing. Coverage in `pyproject.toml` ratchets in the same commit.

## 3. Errata watch

- RFC 7854 carries 3 verified errata and is updated by RFC 8671, RFC 9069, RFC 9515 and RFC 9736. Read all of them before M1. RFC 9515 only changes registration procedures for several BMP registries; RFC 9736 gives the Peer Up message its own namespace and moves codepoints from RFC 8671 and RFC 9069 into it (rfclib, 2026-11-07). RFC 9515 and RFC 9736 report no verified errata.
- RFC 8671 and RFC 9069 report no errata as of 2026-10-29.

## 4. Deliberate non-goals

| Non-goal | Status | Revisit when |
|---|---|---|
| a time series store or a web UI; it emits objects to whatever you have | `[no]` | a named document requires it |
| router configuration: BMP is a monitoring channel and this library never writes to one | `[no]` | a named document requires it |
| BGP speaker behaviour, which is pathattr's boundary and below | `[no]` | a named document requires it |

## 5. Open questions

- messages.decode_statistics is placed on M4, the rung that names statistics, but M1 is the message codec: keep it on M4 or move it to M1
- RFC 9736 moves Peer Up onto its own namespace and RFC 9515 changes registry procedures only: does M1 decode Peer Up information against the RFC 9736 registry, and does a row need to name it

## 6. Publication checklist

- [ ] every `[ ]` row above either `[ok]` or moved to a named later milestone
- [ ] `docs/research.md` claims re-verified and the dated ones either promoted or deleted
- [ ] interoperability evidence recorded in `docs/` against a non-Python implementation
- [ ] `tools/check_dist.py` proves the wheel ships the fixtures the README promises
- [ ] version 0.1.0 tagged, trusted publisher configured, README badges uncommented
