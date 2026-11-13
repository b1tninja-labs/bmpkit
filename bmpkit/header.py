"""BMP common header and per-peer header (RFC 7854 sections 4.1 and 4.2, RFC 8671 section 4, RFC 9069 section 4).

The common header is six octets: version (3), a four octet message length that counts the
header itself, and a message type. A message type the library does not know is *returned*,
never raised: RFC 7854 section 4.1 says an implementation MUST ignore unrecognised types, and
ignoring is the caller's decision. Version 0 is reserved and 1 and 2 were draft versions, so
anything but 3 is refused.

The per-peer header is 42 octets. Peer flags are read in the way the peer type dictates:

* types 0 to 2 (RFC 7854) use ``V L A`` and, since RFC 8671, ``O``; bit 0 is the most
  significant bit of the octet in every figure, so ``V`` is 0x80;
* type 3, the Loc-RIB Instance Peer of RFC 9069 section 4, uses only ``F`` at that same
  0x80 bit. ``V``, ``L``, ``A`` and ``O`` are then all false, because the bit they would use
  means something else, and the peer address is zero-filled and reported as ``None``
  (RFC 9069 section 5.1).

Reserved bits are ignored on receipt (RFC 7854 section 4.2, RFC 8671 section 4, RFC 9069
section 4.2). The L flag is meaningful only for Route Monitoring messages (RFC 7854 erratum
7703, verified); this module only exposes the bit and does not interpret it.

Nothing here decodes a BGP PDU. Those bytes are kept as bytes; decoding them is the job of
``pathattr`` and is tracked in ROADMAP.md.
"""

from __future__ import annotations

import datetime
import enum
import ipaddress
import struct
from dataclasses import dataclass

__all__ = [
    "COMMON_HEADER_LENGTH",
    "MAX_MESSAGE_LENGTH",
    "PER_PEER_HEADER_LENGTH",
    "SUPPORTED_VERSION",
    "BmpError",
    "CommonHeader",
    "MsgType",
    "PeerType",
    "PerPeerHeader",
    "decode_common",
    "decode_per_peer",
    "frame",
]

SUPPORTED_VERSION = 3
COMMON_HEADER_LENGTH = 6
PER_PEER_HEADER_LENGTH = 42
# Policy, not from the RFC: the largest message a decoder accepts by default. A BMP message can
# carry a 65535 octet BGP PDU (RFC 8654) plus headers and TLVs; one MiB leaves wide margin and
# stops a four-gigabyte length field from becoming an allocation.
MAX_MESSAGE_LENGTH = 1 << 20

_V = 0x80
_L = 0x40
_A = 0x20
_O = 0x10
_F = 0x80
_LOC_RIB = 3


class BmpError(ValueError):
    """A BMP message that cannot be decoded. Decoders raise this and nothing else."""


class MsgType(enum.IntEnum):
    """Message types, RFC 7854 section 4.1."""

    ROUTE_MONITORING = 0
    STATISTICS_REPORT = 1
    PEER_DOWN = 2
    PEER_UP = 3
    INITIATION = 4
    TERMINATION = 5
    ROUTE_MIRRORING = 6


class PeerType(enum.IntEnum):
    """Peer types: RFC 7854 section 4.2 (0 to 2) and RFC 9069 section 4.1 (3)."""

    GLOBAL = 0
    RD_INSTANCE = 1
    LOCAL_INSTANCE = 2
    LOC_RIB = 3


@dataclass(frozen=True)
class CommonHeader:
    """The six octet common header. ``msg_type`` is a plain int so unknown types are representable."""

    version: int
    length: int
    msg_type: int

    @property
    def known_type(self) -> MsgType | None:
        """The :class:`MsgType`, or ``None`` for a type this library does not define."""
        try:
            return MsgType(self.msg_type)
        except ValueError:
            return None


@dataclass(frozen=True)
class PerPeerHeader:
    """The 42 octet per-peer header.

    ``peer_type`` and ``flags`` are kept raw. ``address`` is ``None`` for the Loc-RIB Instance
    Peer, whose address is zero-filled and not applicable (RFC 9069 section 5.1).
    ``timestamp`` is ``(seconds, microseconds)``; both zero means unavailable (RFC 7854
    section 4.2).
    """

    peer_type: int
    flags: int
    distinguisher: bytes
    address: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    asn: int
    bgp_id: ipaddress.IPv4Address
    timestamp: tuple[int, int]

    @property
    def is_loc_rib(self) -> bool:
        return self.peer_type == _LOC_RIB

    @property
    def ipv6(self) -> bool:
        """The V flag: the peer address is IPv6. False for the Loc-RIB Instance Peer."""
        return not self.is_loc_rib and bool(self.flags & _V)

    @property
    def post_policy(self) -> bool:
        """The L flag: post-policy (True) or pre-policy (False). Significant only for Route Monitoring."""
        return not self.is_loc_rib and bool(self.flags & _L)

    @property
    def legacy_as_path(self) -> bool:
        """The A flag: legacy 2-octet AS_PATH format (RFC 7854 section 4.2). False for Loc-RIB."""
        return not self.is_loc_rib and bool(self.flags & _A)

    @property
    def adj_rib_out(self) -> bool:
        """The O flag: Adj-RIB-Out (True) or Adj-RIB-In (False), RFC 8671 section 4. False for Loc-RIB."""
        return not self.is_loc_rib and bool(self.flags & _O)

    @property
    def loc_rib_filtered(self) -> bool:
        """The F flag: the Loc-RIB is filtered (RFC 9069 section 4.2). False for every other peer type."""
        return self.is_loc_rib and bool(self.flags & _F)

    @property
    def timestamp_available(self) -> bool:
        return self.timestamp != (0, 0)

    @property
    def time(self) -> datetime.datetime | None:
        """The timestamp as an aware UTC datetime, or ``None`` when it is zero (unavailable)."""
        if not self.timestamp_available:
            return None
        epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
        seconds, micros = self.timestamp
        return epoch + datetime.timedelta(seconds=seconds, microseconds=micros)


def decode_common(raw: bytes, *, max_length: int | None = MAX_MESSAGE_LENGTH) -> CommonHeader:
    """Decode the common header at the start of ``raw`` (RFC 7854 section 4.1).

    Reads exactly six octets and never looks at the body. Raises :class:`BmpError` for fewer than
    six octets, a version other than 3, a length below six, and a length above ``max_length``
    (pass ``None`` to disable that cap). An unknown message type is not an error.
    """
    if len(raw) < COMMON_HEADER_LENGTH:
        raise BmpError(f"common header needs {COMMON_HEADER_LENGTH} octets, got {len(raw)}")
    version, length, msg_type = struct.unpack_from(">BIB", raw, 0)
    if version != SUPPORTED_VERSION:
        raise BmpError(f"unsupported BMP version {version}; only 3 is defined")
    if length < COMMON_HEADER_LENGTH:
        raise BmpError(f"message length {length} is shorter than the common header")
    if max_length is not None and length > max_length:
        raise BmpError(f"message length {length} exceeds the limit {max_length}")
    return CommonHeader(version, length, msg_type)


def frame(raw: bytes, *, max_length: int | None = MAX_MESSAGE_LENGTH) -> tuple[CommonHeader, bytes]:
    """Split one complete message into its header and the body that follows it.

    ``raw`` must hold at least ``length`` octets; extra octets after the message are not read.
    Raises :class:`BmpError` when the message is cut short.
    """
    header = decode_common(raw, max_length=max_length)
    if len(raw) < header.length:
        raise BmpError(f"message is {len(raw)} octets but its length field says {header.length}")
    return header, bytes(raw[COMMON_HEADER_LENGTH : header.length])


def decode_per_peer(raw: bytes, *, strict: bool = True) -> PerPeerHeader:
    """Decode the 42 octet per-peer header at the start of ``raw`` (RFC 7854 section 4.2).

    Applies the RFC 8671 O flag and the RFC 9069 Loc-RIB peer type as described in the module
    docstring. With ``strict`` an IPv4 peer whose twelve leading address octets are not zero is
    refused; the RFC says they are zero-filled. Without it the low four octets are used.
    Raises :class:`BmpError` for fewer than 42 octets.
    """
    if len(raw) < PER_PEER_HEADER_LENGTH:
        raise BmpError(f"per-peer header needs {PER_PEER_HEADER_LENGTH} octets, got {len(raw)}")
    peer_type, flags, distinguisher, address, asn, bgp_id, seconds, micros = struct.unpack_from(
        ">BB8s16sI4sII", raw, 0
    )
    header = PerPeerHeader(
        peer_type, flags, distinguisher, None, asn, ipaddress.IPv4Address(bgp_id), (seconds, micros)
    )
    if header.is_loc_rib:
        return header
    parsed: ipaddress.IPv4Address | ipaddress.IPv6Address
    if header.ipv6:
        parsed = ipaddress.IPv6Address(address)
    else:
        if strict and address[:12] != bytes(12):
            raise BmpError("IPv4 peer address is not zero-filled in its twelve leading octets")
        parsed = ipaddress.IPv4Address(address[12:])
    return PerPeerHeader(
        peer_type, flags, distinguisher, parsed, asn, header.bgp_id, (seconds, micros)
    )
