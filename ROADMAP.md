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
| `header.decode_common()` | RFC 7854 section 4.1 | `[ok]` | `tests/test_header.py::test_common_header_version3_route_monitoring`, `tests/test_header.py::test_common_header_rejects_version_0_1_2_4`, `tests/test_header.py::test_common_header_unknown_type_is_returned_not_error` | M1 |
| `header.decode_per_peer()` | RFC 7854 section 4.2; RFC 8671 section 4; RFC 9069 sections 4 and 5.1 | `[ok]` | `tests/test_header.py::test_per_peer_o_flag_adj_rib_out`, `tests/test_header.py::test_per_peer_loc_rib_type3_f_flag_and_zero_address`, `tests/test_header.py::test_per_peer_ipv6` | M1 |
| `header.frame()` | RFC 7854 section 4.1 | `[ok]` | `tests/test_header.py::test_frame_returns_exactly_length_octets_of_message`, `tests/test_header.py::test_frame_refuses_a_message_cut_short` | M1 |
| `messages.decode_initiation()` | RFC 7854 sections 4.3 and 4.4; RFC 9736 section 3.1 | `[ok]` | `tests/test_messages.py::test_initiation_with_sysdescr_sysname`, `tests/test_messages.py::test_initiation_rfc9736_peer_up_types_are_reserved_not_strings` | M1 |
| `messages.decode_termination()` | RFC 7854 section 4.5 | `[ok]` | `tests/test_messages.py::test_termination_each_reason_code_0_to_4`, `tests/test_messages.py::test_termination_reason_required` | M1 |
| `messages.decode_peer_up()` | RFC 7854 section 4.10; RFC 9736 section 3.3; RFC 9069 section 5.2 | `[ok]` | `tests/test_messages.py::test_peer_up_ipv4_with_rfc9736_tlvs`, `tests/test_messages.py::test_peer_up_rfc9736_reserved_types_1_and_2_are_kept_not_interpreted`, `tests/test_messages.py::test_peer_up_loc_rib_has_no_local_address` | M1 |
| `messages.decode_tlvs()` | RFC 7854 section 4.4 | `[ok]` | `tests/test_messages.py::test_tlv_length_overruns_body`, `tests/test_messages.py::test_too_many_tlvs_refused` | M1 |
| `messages.decode-peer-down` | RFC 7854 section 4.9 (not yet read); errata 4830 and 7194 | `[ ]` | `tests/test_messages.py::test_decode_peer_down` (to be written) | M1 |
| `messages.decode-route-mirroring` | RFC 7854 section 4.7 (not yet read) | `[ ]` | `tests/test_messages.py::test_decode_route_mirroring` (to be written) | M4 |
| `messages.decode-bgp-pdus` | RFC 7854 sections 4.6, 4.7 and 4.10 with pathattr; RFC 4271, RFC 7606 | `[ ]` | `tests/test_pathattr_link.py::test_decode_bgp_pdus` (to be written) | M1 |
| `server.limits` | RFC 7854 section 3.3 (Initiation MUST be first); design | `[ ]` | `tests/test_server.py::test_limits` (to be written) | M2 |
| `store.capture-format` | design | `[ ]` | `tests/test_store.py::test_capture_format` (to be written) | M5 |
| `header.capture-fixtures` | RFC 7854 (interoperability evidence) | `[ ]` | `tests/test_header.py::test_captured_frr_header` (to be written) | M1 |
| `messages.decode_route_monitoring()` | RFC 7854 sections 4.6 and 5 (not yet read); needs pathattr for the BGP UPDATE | `[ ]` | `tests/test_obligations.py::test_decode_route_monitoring` (to be written) | M1 |
| `messages.decode_statistics()` | RFC 7854 section 4.8 (not yet read) | `[ ]` | `tests/test_obligations.py::test_decode_statistics` (to be written) | M1 |
| `rib.view_of()` | RFC 8671, RFC 9069 | `[ ]` | `tests/test_obligations.py::test_view_of` (to be written) | M3 |
| `server.serve()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::test_serve` (to be written) | M2 |
| `mirror.extract_bgp_message()` | RFC 7854 section 4.7 (not yet read) | `[ ]` | `tests/test_obligations.py::test_extract_bgp_message` (to be written) | M4 |
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
- RFC 7854 verified errata, read 2026-11-13: 4722 (editorial, "Stats Reports" against the IANA name "Statistics Report"); 7194 (technical, section 10.8: the Peer Down reason registry ranges are for a one-octet field, not 0 to 65535); 7703 (technical, section 4.2: the L flag is significant only for Route Monitoring, not merely not for mirroring). Held for document update, not verified: 4830 (section 4.9, whether Peer Down carries the per-peer header), 5736 (editorial figure), 7133 (section 5, End-of-RIB is per address family and not per peer). 4830 matters to `messages.decode-peer-down`: read section 4.9 and these before coding.
- RFC 9736 (read 2026-11-13) is applied: Initiation and Peer Up have separate TLV namespaces. Initiation: 0 String, 1 sysDescr, 2 sysName, 3 and 4 Reserved. Peer Up: 0 String, 3 VRF/Table Name, 4 Admin Label, 1 and 2 Reserved. RFC 9515 changes registration procedure only (32768-65530 becomes First Come First Served); no wire change.
- RFC 9069 puts the F flag at the 0x80 bit of the peer flags octet for peer type 3, the same bit V uses for types 0 to 2, so flags must be read according to the peer type (done in `header.PerPeerHeader`).

## 4. Deliberate non-goals

| Non-goal | Status | Revisit when |
|---|---|---|
| a time series store or a web UI; it emits objects to whatever you have | `[no]` | a named document requires it |
| router configuration: BMP is a monitoring channel and this library never writes to one | `[no]` | a named document requires it |
| BGP speaker behaviour, which is pathattr's boundary and below | `[no]` | a named document requires it |

## 5. Open questions

- **Resolved 2026-11-13.** `messages.decode_statistics` moved from M4 to M1: statistics are counters with no BGP dependency, and M1 is the message codec.
- **Resolved 2026-11-13.** M1 decodes Peer Up Information against the RFC 9736 Peer Up registry (`decode_peer_up`), and the Initiation message against the RFC 9736 Initiation registry. RFC 9515 needs no row: it changes registration procedure only.
- **Dependency on pathattr.** `docs/plan.md` said "Depends on: None". Route Monitoring, Route Mirroring and the OPEN messages inside Peer Up carry BGP PDUs, and decoding them is pathattr's job (`D:\code\pathattr`, being built elsewhere). bmpkit decodes the BMP framing itself and keeps PDU bodies as bytes; `messages.decode-bgp-pdus` is the row that links them. The workspace plan (PORTFOLIO.md) should carry the arrow; `docs/plan.md` is generated and was corrected by hand here.
- **Strictness.** `strict=True` refuses an Initiation without sysDescr or sysName, a Termination without a Reason, non-UTF-8 strings, and a non-zero-filled IPv4 address; `strict=False` reports or keeps them. Real routers should be sampled before the defaults are final.
- **Message length cap.** `MAX_MESSAGE_LENGTH` (1 MiB) is policy, not from the RFC. Revisit with RFC 8654 extended messages in the server row.
- **bgpfeed.** The normalised event model is shared with bgpfeed's README; one owner has to be chosen before `rib.view_of`.

## 6. Publication checklist

- [ ] every `[ ]` row above either `[ok]` or moved to a named later milestone
- [ ] `docs/research.md` claims re-verified and the dated ones either promoted or deleted
- [ ] interoperability evidence recorded in `docs/` against a non-Python implementation
- [ ] `tools/check_dist.py` proves the wheel ships the fixtures the README promises
- [ ] version 0.1.0 tagged, trusted publisher configured, README badges uncommented
