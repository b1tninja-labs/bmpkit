# Changelog

The format follows Keep a Changelog, and this project adheres to Semantic Versioning.

## Unreleased

### Added

- `header`: the BMP common header (version 3, unknown message types returned rather than raised),
  `frame`, and the per-peer header with the RFC 8671 O flag and the RFC 9069 Loc-RIB peer type and F flag.
- `messages`: Information TLVs, Initiation, Termination and Peer Up, with the RFC 9736 Initiation and
  Peer Up TLV namespaces. BGP OPEN messages are returned as bytes.

The rest of the package is a shell: the public surface exists as typed stubs that raise
`NotImplementedError`, and [ROADMAP.md](ROADMAP.md) lists what has to happen first.

## 0.0.0 - 2026-11-05

### Added

- Package skeleton, obligation matrix and CI gates for bmpkit.
- `bmpkit.apps` namespace reserved for composition that is not protocol behaviour.
