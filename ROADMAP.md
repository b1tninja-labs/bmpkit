# Specification completeness -- and the roadmap it implies

This is the project's north star: every protocol obligation bmpkit could plausibly take on,
with an honest status against the code at `HEAD`. It is blunt about gaps on purpose. A
roadmap that overstates its coverage is not a plan, it is marketing.

**The honesty rule:** a row may read `[ok]` only when a named test would fail if the
behaviour regressed. Reading the code and agreeing with it is not enough. That is how
"decoded but never sent" quietly becomes "implemented".

Legend: `[ok]` implemented and pinned by a named test -- `[part]` partial, with what is
missing stated -- `[ ]` not implemented -- `[no]` deliberate non-goal.

Update the affected row in the same commit that changes the behaviour. A row and its test
drift apart within one release, and the document becomes useless exactly when it is needed.

## 1. Obligations

| Obligation | Spec | Status | Where |
|---|---|---|---|
| `header.decode_common()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::decode_common` |
| `messages.decode_route_monitoring()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::decode_route_monitoring` |
| `messages.decode_statistics()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::decode_statistics` |
| `rib.view_of()` | RFC 8671, RFC 9069 | `[ ]` | `tests/test_obligations.py::view_of` |
| `server.serve()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::serve` |
| `mirror.extract_bgp_message()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::extract_bgp_message` |
| `replay.from_capture()` | design | `[ ]` | `tests/test_obligations.py::from_capture` |

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

- RFC 7854 carries 3 verified errata and is updated by RFC 8671, RFC 9069, RFC 9515 and RFC 9736. Read all of them before M1: RFC 9515 and RFC 9736 were not examined during this survey and may change message handling.
- RFC 8671 and RFC 9069 report no errata as of 2026-10-29.

## 4. Deliberate non-goals

| Non-goal | Status | Revisit when |
|---|---|---|
| a time series store or a web UI; it emits objects to whatever you have | `[no]` | a named document requires it |
| router configuration: BMP is a monitoring channel and this library never writes to one | `[no]` | a named document requires it |
| BGP speaker behaviour, which is pathattr's boundary and below | `[no]` | a named document requires it |

## 5. Open questions

- none recorded yet

## 6. Publication checklist

- [ ] every `[ ]` row above either `[ok]` or moved to a named later milestone
- [ ] `docs/research.md` claims re-verified and the dated ones either promoted or deleted
- [ ] interoperability evidence recorded in `docs/` against a non-Python implementation
- [ ] `tools/check_dist.py` proves the wheel ships the fixtures the README promises
- [ ] version 0.1.0 tagged, trusted publisher configured, README badges uncommented
