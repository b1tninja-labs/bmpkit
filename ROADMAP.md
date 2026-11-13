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
| `messages.decode-peer-down` | RFC 7854 section 4.9 read in full: the body follows the common header and the per-peer header (held erratum 4830 asks for that sentence); reason is one octet (verified erratum 7194 corrects section 10.8's 16-bit ranges, and the IANA registry agrees); reason 6 and its VRF/Table Name TLV from RFC 9069 section 5.3 | `[ok]` | `tests/test_pathattr_link.py::test_peer_down_body_follows_common_and_per_peer_header_erratum_4830`, `tests/test_pathattr_link.py::test_peer_down_each_defined_reason`, `tests/test_pathattr_link.py::test_peer_down_reason_six_carries_a_vrf_name_tlv_rfc_9069`, `tests/test_pathattr_link.py::test_peer_down_malformed_is_refused_when_strict` | M1 |
| `messages.decode-route-mirroring` | RFC 7854 section 4.7 read in full: BGP Message TLV (type 0) last, Information TLV (type 1) two octets, Errored PDU needs a BGP Message TLV | `[ok]` | `tests/test_pathattr_link.py::test_route_mirroring_splits_information_and_bgp_message`, `tests/test_pathattr_link.py::test_route_mirroring_violations_are_refused_when_strict`, `tests/test_pathattr_link.py::test_route_mirroring_messages_lost_has_no_pdu` | M4 |
| `messages.decode-bgp-pdus` | RFC 7854 sections 4.6, 4.7 and 4.10 with pathattr as a sibling path dependency (`pyproject.toml` pytest `pythonpath` and mypy `mypy_path`; the `codec` extra for installs): `decode_bgp_pdu`, A flag selects 2-octet AS_PATH, `internal=True` so post-policy LOCAL_PREF is kept | `[ok]` | `tests/test_pathattr_link.py::test_route_monitoring_decodes_the_update_with_pathattr`, `tests/test_pathattr_link.py::test_route_monitoring_l_flag_and_a_flag_come_from_the_per_peer_header`, `tests/test_pathattr_link.py::test_route_mirroring_errored_pdu_may_not_decode_but_stays_available` | M1 |
| `server.limits` | RFC 7854 section 3.3 (Initiation MUST be first), section 4.1 (unknown types ignored), section 3.2 (the per-address and rate shape); the numbers are design. `server.Connection` frames a byte stream under `Limits` (message length, peers, Initiation first, closed after Termination) and `server.Admission` limits connections per address and per window; both are sans-IO, and `serve()` stays a stub (row `server.serve()`) | `[ok]` | `tests/test_server.py::test_the_first_message_must_be_an_initiation`, `tests/test_server.py::test_unknown_types_are_returned_after_initiation_and_bytes_may_arrive_split`, `tests/test_server.py::test_a_length_over_the_limit_is_refused_from_the_header_alone`, `tests/test_server.py::test_peer_up_beyond_max_peers_is_refused_and_peer_down_frees_a_slot`, `tests/test_server.py::test_admission_limits_concurrent_connections_per_address`, `tests/test_server.py::test_admission_limits_the_connection_rate_over_a_window` | M2 |
| `store.capture-format` | design | `[ ]` | `tests/test_store.py::test_capture_format` (to be written) | M5 |
| `header.capture-fixtures` | RFC 7854 (interoperability evidence) | `[ ]` | `tests/test_header.py::test_captured_frr_header` (to be written) | M1 |
| `messages.decode_route_monitoring()` | RFC 7854 sections 4.6 and 5 read in full: one UPDATE, L flag, End-of-RIB reported per (AFI, SAFI) because RFC 4724 defines it per family (held erratum 7133 says RFC 7854 section 5 is wrong to ask for one per peer); optional `pathattr.limits.Budget` | `[ok]` | `tests/test_pathattr_link.py::test_route_monitoring_decodes_the_update_with_pathattr`, `tests/test_pathattr_link.py::test_route_monitoring_end_of_rib_markers`, `tests/test_pathattr_link.py::test_route_monitoring_refuses_non_update_and_garbage`, `tests/test_pathattr_link.py::test_route_monitoring_budget_refuses_an_oversized_update` | M1 |
| `messages.add_path_families()` | RFC 7911 section 5 applied to the two OPENs of a Peer Up: Adj-RIB-In needs local Receive and peer Send, Adj-RIB-Out the reverse (an inference: RFC 8671 does not mention ADD-PATH), Loc-RIB lists whatever the fabricated OPEN carries (RFC 9069 section 5.2) | `[ok]` | `tests/test_pathattr_link.py::test_add_path_families_follow_the_direction_of_the_rib`, `tests/test_pathattr_link.py::test_add_path_families_loc_rib_counts_any_listed_family_rfc_9069_5_2`, `tests/test_pathattr_link.py::test_route_monitoring_with_add_path_reads_path_identifiers` | M3 |
| bmp.addpath-adj-rib-out-direction | verify against a real BMP capture that Adj-RIB-Out messages carry Path Identifiers exactly for local-Send and peer-Receive families; no RFC says so | `[ ]` | `tests/test_obligations.py::test_addpath_adj_rib_out (to be written)` | M6 |
| bmp.stats-rfc-9972 | the IANA statistics registry (updated 2026-05-22) now holds types 14 to 17 from RFC 8671 and 18 to 43 from RFC 9972, which the spine does not list; read RFC 9972 before writing `decode_statistics` Done 2026-11-13: RFC 9972 (Proposed Standard, 2026-05, current, no errata) sections 3.1 to 3.3 and 8 read; the rules of section 3.1 (length 8 or 11, each global statistic once, no duplicate (AFI, SAFI)) are enforced in strict mode for types 18 to 43. Section 4 (which statistics apply to Loc-RIB) is not enforced: it is a statement about the sender, and the per-peer header type is not checked against the statistic. | `[ok]` | `tests/test_messages.py::test_statistics_report_reads_counters_gauges_and_per_family_gauges`, `tests/test_messages.py::test_a_statistics_report_that_breaks_its_rules_is_refused` | M4 |
| bmp.route-monitoring-internal-flag | `decode_bgp_pdu` assumes an internal session (`internal=True`) so RFC 7606 section 7.5 does not discard post-policy LOCAL_PREF; deriving IBGP or EBGP from the Peer Up OPENs would be exact | `[ ]` | `tests/test_obligations.py::test_internal_from_peer_up (to be written)` | M3 |
| bmp.peer-down-informational-tlvs | Peer Down reason 6 TLVs other than VRF/Table Name (type 3) are returned raw in `tlvs`; RFC 9069 section 5.3 defines only type 3 Checked 2026-11-13: RFC 9069 section 5.3 defines only type 3 for reason 6 and rfclib finds no other document defining a Peer Down TLV, so raw is the whole answer; a later document defining one changes this row. | `[ok]` | `tests/test_messages.py::test_peer_down_tlvs_other_than_the_vrf_name_are_kept_raw` | M4 |
| `messages.decode_statistics()` | RFC 7854 section 4.8 (not yet read) Done 2026-11-13 (section 4.8 read in full; erratum 4722 is editorial). Types by their documents: counters 0 to 6 and 11 to 13 (32-bit), gauges 7, 8 (RFC 7854), 14 and 15 (RFC 8671 table 2), 18, 20, 29, 31, 33, 39 (RFC 9972), and the per-AFI/SAFI gauges 9, 10, 16, 17 and 19, 21 to 23, 26 to 28, 30, 32, 34 to 38, 40 to 43. Types 24, 25 and 44 up are kept as `unknown`. Vectors are built from the layouts; the specs print no bytes. | `[ok]` | `tests/test_messages.py::test_statistics_report_reads_counters_gauges_and_per_family_gauges`, `tests/test_messages.py::test_statistics_unknown_types_are_kept_and_not_interpreted`, `tests/test_messages.py::test_a_statistics_report_that_breaks_its_rules_is_refused`, `tests/test_messages.py::test_statistics_without_strict_keep_what_strict_refuses` | M1 |
| `rib.view_of()` | RFC 8671 section 4 (O flag, L flag; section 5.1 and 5.2 say L MUST be 1 post-policy and 0 pre-policy) and RFC 9069 sections 4.1 and 4.2 (peer type 3 ignores every flag but F). `rib.view_of(peer_type, flags)` returns a bmpkit `View` with bgpfeed's five values and no bgpfeed import; `loc_rib_filtered` reads F | `[ok]` | `tests/test_rib.py::test_o_and_l_flags_select_the_view_for_peer_types_0_to_2`, `tests/test_rib.py::test_loc_rib_ignores_every_flag_and_f_is_the_only_one_that_means_something`, `tests/test_rib.py::test_it_agrees_with_the_header_property_and_with_bgpfeed_for_every_flag` | M3 |
| `events.bgpfeed-event` | `bmpkit.events` emits `bgpfeed.model.Event` from Route Monitoring (an ANNOUNCE or WITHDRAW per prefix, IPv4 and MP_REACH/MP_UNREACH, treat-as-withdraw as a WITHDRAW with a reason, an untrusted UPDATE refused), Peer Up (`session` UP) and Peer Down (`session` DOWN, `reason` from the code). `time` is `None` for a zero per-peer timestamp (RFC 7854 section 4.2), `Peer.address` is `None` for the Loc-RIB Instance Peer (RFC 9069 section 5.1), `view` is read from peer type and the L and O flags (RFC 7854 section 4.2, RFC 8671 sections 4 and 5, RFC 9069 section 4), the peer distinguisher and BGP ID ride on `Peer`. The mapping is written here against pathattr, not taken from `bgpfeed.mrt`; sharing one UPDATE-to-events module with bgpfeed is the open part (bgpfeed row `model.Event`). Not covered: Loc-RIB F flag as a field, Termination, Statistics and Route Mirroring events | `[ok]` | `tests/test_events.py::test_route_monitoring_events`, `tests/test_events.py::test_the_loc_rib_instance_peer_has_no_address_and_its_own_view`, `tests/test_events.py::test_peer_down_and_up_events_carry_a_session_state_and_no_fsm_numbers` | M3 |
| `server.serve()` | RFC 7854 | `[ ]` | `tests/test_obligations.py::test_serve` (to be written) | M2 |
| `mirror.extract_bgp_message()` | RFC 7854 section 4.7: the verbatim PDU of the BGP Message TLV; `decode_mirrored` adds the pathattr decode | `[ok]` | `tests/test_pathattr_link.py::test_route_mirroring_splits_information_and_bgp_message`, `tests/test_pathattr_link.py::test_route_mirroring_messages_lost_has_no_pdu` | M4 |
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
- **bgpfeed.** The normalised event model is bgpfeed's (`bgpfeed.model.Event`, PORTFOLIO section 9 item 15). It fits BMP since 2026-11-13 (optional time and peer address, view, distinguisher, BGP ID, a session state without FSM numbers); `bmpkit.events` emits it, see the row `events.bgpfeed-event`.

## 6. Publication checklist

- [ ] every `[ ]` row above either `[ok]` or moved to a named later milestone
- [ ] `docs/research.md` claims re-verified and the dated ones either promoted or deleted
- [ ] interoperability evidence recorded in `docs/` against a non-Python implementation
- [ ] `tools/check_dist.py` proves the wheel ships the fixtures the README promises
- [ ] version 0.1.0 tagged, trusted publisher configured, README badges uncommented
