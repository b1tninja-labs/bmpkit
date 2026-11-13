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

RFC 7854 sections 3.3, 4.1, 4.2, 4.3, 4.4, 4.5 and 4.10; RFC 8671 section 4; RFC 9069 sections 4 and 5.2 (5.1 by search only); RFC 9736 in full; RFC 9515 abstract only; RFC 4271 section 4.1. Not yet read: RFC 7854 sections 4.6 to 4.9, 5 to 8 and 10.

Test vectors: none of these RFCs has byte examples. Every vector in `tests/` is built by hand from the figures and field lists and says so. A capture from a live FRR or BIRD speaker is a ROADMAP row and the only interoperability evidence still owed.

Further documents the project will need, not yet in the spine: RFC 6793 (the A flag), RFC 7911 (ADD-PATH in monitored UPDATEs), RFC 5492 and RFC 8810 (capabilities in OPENs), RFC 8654 and RFC 9072 (extended messages), RFC 4364 (route distinguishers in RD Instance Peers), RFC 7606 (UPDATE error handling).
