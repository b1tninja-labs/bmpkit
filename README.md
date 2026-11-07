# bmpkit

<!-- PyPI badges go live with the first release. Until then a version badge renders
     "no version" on the landing page, which reads as a defect rather than a date, so
     the badges stay commented out until the tag exists.
-->

**Pre-alpha shell.** The package surface, the obligation matrix and the CI gates exist.
No protocol behaviour is implemented: every public function raises `NotImplementedError`,
and the test suite records that rather than hiding it. Read
[ROADMAP.md](ROADMAP.md) before depending on any of it.

bmpkit -- stop screen scraping your routers

BMP exists precisely because obtaining route views used to mean scraping a terminal, and Python still cannot consume it. FRR, BIRD, Cisco and Juniper all emit BMP; nothing in Python reads it. The name bmp on PyPI is a retrieval library and pybmp is a BMP image handler, so the acronym is unclaimed in this sense. bmpkit decodes to the same update objects pathattr defines and hands them to a store, which is exactly the seam a looking glass, an analyst tool and a hijack detector all need.

## The gap, with a date

PyPI was queried on 2026-11-05 for this name and for every neighbouring project. Landscape
claims rot quickly: two projects in this portfolio shipped within five days of the survey,
which is why the table below carries dates instead of adjectives.

| Project | Version | Last release | Why it is not this project |
|---|---|---|---|
| bmp | 0.2.8 | 2026-10-16 | block-max learned sparse retrieval, unrelated |
| pybmp | 1.0.1 | 2016-11-05 | a BMP image handler |
| GoBGP and HurricanE Electric BMP tooling | - | - | Go and C; no importable Python consumer |

What this project intends to add:

- a collector that terminates many router sessions with per-peer state and no head-of-line blocking
- route mirroring passthrough, which is how you debug a session without touching the router
- correct handling of the three RIB views: Adj-RIB-In, Adj-RIB-Out and Loc-RIB
- stats and termination records with reason codes, so gaps in the mirrored view are visible rather than silent
- reconnect and sequence discipline, because TCP carries BMP and reordering is a real analyst hazard

## Specification spine

Status and publication dates below were read from the RFC Editor record on 2026-11-05. A
section number is cited only where that section was read in full; everything else cites the
document, which is the honest grain size for a plan. See [docs/rfc-map.md](docs/rfc-map.md).

| Document | Status | Published | What it gives this project |
|---|---|---|---|
| RFC 7854 | Proposed Standard | 2016-06 | BMP: common header, per peer header, route monitoring, statistics, termination and route mirroring |
| RFC 8671 | Proposed Standard | 2019-11 | Adj-RIB-Out mirroring and the peer flag that distinguishes it |
| RFC 9069 | Proposed Standard | 2022-02 | Loc-RIB access, the selected routes rather than the received ones |

### Errata watch

- RFC 7854 carries 3 verified errata and is updated by RFC 8671, RFC 9069, RFC 9515 and RFC 9736. Read all of them before M1. RFC 9515 only changes registration procedures for several BMP registries; RFC 9736 gives the Peer Up message its own namespace and moves codepoints from RFC 8671 and RFC 9069 into it (rfclib, 2026-11-07). RFC 9515 and RFC 9736 report no verified errata.
- RFC 8671 and RFC 9069 report no errata as of 2026-10-29.

## Module layout

| Module | Responsibility |
|---|---|
| `header` | common and per peer headers with the version and flag discipline (RFC 7854) |
| `messages` | route monitoring, statistics, peer down and up, initiation and termination, route mirroring (RFC 7854) |
| `rib` | view selection across Adj-RIB-In, Adj-RIB-Out and Loc-RIB (RFC 8671, RFC 9069) |
| `server` | the asyncio collector with per connection state |
| `mirror` | passthrough of mirrored traffic for capture and replay |
| `store` | the sink interface a mirrored RIB is written to |
| `replay` | deterministic re-reading of a capture for tests and analysts |

## What it does not do

- a time series store or a web UI; it emits objects to whatever you have
- router configuration: BMP is a monitoring channel and this library never writes to one
- BGP speaker behaviour, which is pathattr's boundary and below


## Install

```bash
git clone https://github.com/b1tninja/bmpkit.git
cd bmpkit
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
```

Not published to PyPI yet. The name is reserved for this repository's trusted publisher at
the moment of the first release.

## Development

All four gates must pass, on Linux and Windows alike:

```bash
ruff check . && ruff format --check .
mypy bmpkit
pytest -q --cov
python -O -m pytest -q
```

The last line is the one that matters most in a protocol library. `-O` strips `assert`, and a
parser whose bounds checks were asserts stops being a parser under production flags. Wire
paths raise named exceptions; asserts belong in tests and nowhere else.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
