# Where every claim in this repository comes from

| Document | Status | Published | Verified against the publisher record on |
|---|---|---|---|
| RFC 7854 (updated by RFC 8671, 9069, 9515, 9736) | Proposed Standard, current, 3 verified errata (4722, 7194, 7703) and 3 held (4830, 5736, 7133) | 2016-06 | 2026-11-13 |
| RFC 8671 (updated by RFC 9736) | Proposed Standard, current, no errata; the O flag, Adj-RIB-Out | 2019-11 | 2026-11-13 |
| RFC 9069 (updated by RFC 9736) | Proposed Standard, current, no errata; Peer Type 3 and the F flag, Loc-RIB | 2022-02 | 2026-11-13 |
| RFC 9515 | Proposed Standard, current; updates RFC 7854 registration procedures only | 2023-12 | 2026-11-13 |
| RFC 9736 | Proposed Standard, current, no errata; separate Peer Up and Initiation TLV namespaces; updates RFC 7854, 8671, 9069 | 2025-03 | 2026-11-13 |
| RFC 4271 | Draft Standard, current, 9 verified errata; only section 4.1 (the header length field) is used, to frame OPEN messages | 2006-01 | 2026-11-13 |

Citation rules, in the order they most often get broken:

1. Cite the document. A secondary write-up is a lead, not a source.
2. A section number is cited only if that section was read in full.
3. Errata are checked at each milestone freeze, not once at the start.
4. Where a claim came from a body outside the RFC series, that body is named here.

Re-verify with the RFC library rather than memory: `info('RFCnnnn')` for current status, `errata('RFCnnnn')` for corrections, and `read('RFCnnnn', view='normative')` for the MUST and SHOULD statements that become obligation rows.

## Sections read in full

RFC 7854 sections 3.3, 4.1, 4.2, 4.3, 4.4, 4.5 and 4.10; RFC 8671 section 4; RFC 9069 sections 4 and 5.2 (5.1 by search only); RFC 9736 in full; RFC 9515 abstract only; RFC 4271 section 4.1. Read on 2026-11-13 in the second pass: RFC 7854 sections 4.6, 4.7, 4.9, 5 and 10.8 to 10.10, RFC 9069 sections 5.2 to 5.4 and 8.4. Not yet read: RFC 7854 sections 4.8 (statistics), 6 to 9.

Test vectors: none of these RFCs has byte examples. Every vector in `tests/` is built by hand from the figures and field lists and says so. A capture from a live FRR or BIRD speaker is a ROADMAP row and the only interoperability evidence still owed.

Further documents the project will need, not yet in the spine: RFC 6793 (the A flag), RFC 7911 (ADD-PATH in monitored UPDATEs), RFC 5492 and RFC 8810 (capabilities in OPENs), RFC 8654 and RFC 9072 (extended messages), RFC 4364 (route distinguishers in RD Instance Peers), RFC 7606 (UPDATE error handling).

Findings of the second pass:

- Erratum 4830 (held, technical): the Peer Down figure does not say that the per-peer header precedes the Reason. It does, as in every other message that has one; `decode_peer_down` takes the body after the per-peer header exactly as `decode_peer_up` does, and a test builds the whole message to show it.
- Erratum 7194 (verified, technical): the Peer Down Reason is one octet, so the IANA ranges become 0 reserved, 1 to 127 Standards Action, 128 to 250 Specification Required, 251 to 254 experimental, 255 reserved. The IANA registry (`bmp-parameters`, updated 2026-05-22) already reads that way and also lists reason 6 (RFC 9069).
- Erratum 7703 (verified): the L flag has significance only for Route Monitoring, so `decode_mirrored` does not consult it.
- Erratum 7133 (held): RFC 7854 section 5 asks for one End-of-RIB marker per peer, but RFC 4724 defines the marker per address family. `RouteMonitoring.end_of_rib` reports the family.
- RFC 7854 section 4.7 in the IANA registries: Route Mirroring TLV types 0 and 1 and Information codes 0 and 1 are the only assigned values.
- RFC 9972 (statistics types 18 to 43) and RFC 8671 types 14 to 17 are in the IANA statistics registry and not in the spine; recorded in `ROADMAP.md`.
- pathattr (RFC 4271, RFC 7606, RFC 7911, RFC 4760) is a sibling path dependency: `pyproject.toml` puts `../pathattr` on pytest's `pythonpath` and mypy's `mypy_path`, as `bgpfeed` does.
