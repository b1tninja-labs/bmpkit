"""BMP message bodies: Initiation, Termination, Peer Up and their TLVs (RFC 7854, RFC 9736).

Every decoder here takes the *body*: the octets after the common header (and after the per-peer
header for Peer Up). Use :func:`bmpkit.header.frame` to get it.

TLVs (RFC 7854 section 4.4 and section 4.5) are a two octet type, a two octet length and the
value. Initiation and Peer Up used to share one type namespace; RFC 9736 splits it, and this
module follows RFC 9736 (Initiation Information TLVs: 0 String, 1 sysDescr, 2 sysName; Peer Up
Information TLVs: 0 String, 3 VRF/Table Name, 4 Admin Label; types 1 and 2 are reserved for
Peer Up and 3 and 4 for Initiation). A type that is not defined for the message is kept in
``other`` unread, never dropped and never guessed at.

Strings are UTF-8 (RFC 9736 section 2). With ``strict`` (the default) bad UTF-8 raises
:class:`~bmpkit.header.BmpError`; without it the bytes are kept with ``surrogateescape`` so the
original octets can be recovered. Order is preserved everywhere: RFC 7854 section 4.4 says the
order of multiple strings MUST be preserved.

BGP OPEN messages inside Peer Up are returned as bytes; decoding them belongs to ``pathattr``.
"""

from __future__ import annotations

import enum
import ipaddress
import struct
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .header import BmpError, PerPeerHeader

if TYPE_CHECKING:
    from typing import Any

    PeerKey = Any  # placeholder: give it a real type in the milestone that needs it
    Stats = Any  # placeholder: give it a real type in the milestone that needs it
    Update = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "MAX_TLVS",
    "InfoTlv",
    "Initiation",
    "PeerUp",
    "TermReason",
    "Termination",
    "decode_initiation",
    "decode_peer_up",
    "decode_route_monitoring",
    "decode_statistics",
    "decode_termination",
    "decode_tlvs",
]

MAX_TLVS = 1024
_TLV_HEADER = 4
_BGP_HEADER = 19
_BGP_OPEN = 1

# RFC 9736 section 3.1 and section 3.3
_INIT_STRING, _INIT_SYS_DESCR, _INIT_SYS_NAME = 0, 1, 2
_UP_STRING, _UP_VRF_NAME, _UP_ADMIN_LABEL = 0, 3, 4
# RFC 7854 section 4.5
_TERM_STRING, _TERM_REASON = 0, 1


class TermReason(enum.IntEnum):
    """Termination reasons, RFC 7854 section 4.5."""

    ADMIN_CLOSED = 0
    UNSPECIFIED = 1
    OUT_OF_RESOURCES = 2
    REDUNDANT_CONNECTION = 3
    PERMANENTLY_ADMIN_CLOSED = 4


@dataclass(frozen=True)
class InfoTlv:
    """One TLV: the type and the unread value octets."""

    type: int
    value: bytes


def decode_tlvs(raw: bytes, *, max_tlvs: int = MAX_TLVS) -> tuple[InfoTlv, ...]:
    """Split ``raw`` into TLVs (RFC 7854 section 4.4), in order, using the whole of ``raw``.

    Raises :class:`BmpError` for a truncated TLV header, a length that runs past the end, and
    more than ``max_tlvs`` TLVs. Trailing octets that cannot form a TLV are an error, not padding.
    """
    found: list[InfoTlv] = []
    at = 0
    end = len(raw)
    while at < end:
        if end - at < _TLV_HEADER:
            raise BmpError(f"{end - at} trailing octets cannot hold a TLV header")
        tlv_type, length = struct.unpack_from(">HH", raw, at)
        at += _TLV_HEADER
        if length > end - at:
            raise BmpError(f"TLV type {tlv_type} says {length} octets but {end - at} remain")
        if len(found) >= max_tlvs:
            raise BmpError(f"more than {max_tlvs} TLVs")
        found.append(InfoTlv(tlv_type, bytes(raw[at : at + length])))
        at += length
    return tuple(found)


def _text(value: bytes, strict: bool) -> str:
    try:
        return value.decode("utf-8", errors="strict" if strict else "surrogateescape")
    except UnicodeDecodeError as error:
        raise BmpError(f"string TLV is not valid UTF-8: {error.reason}") from error


@dataclass(frozen=True)
class Initiation:
    """An Initiation message (RFC 7854 section 4.3, TLV types of RFC 9736 section 3.1)."""

    tlvs: tuple[InfoTlv, ...]
    sys_descr: tuple[str, ...]
    sys_name: tuple[str, ...]
    strings: tuple[str, ...]
    other: tuple[InfoTlv, ...]

    @property
    def missing(self) -> tuple[str, ...]:
        """Names of the TLVs the RFC says MUST be sent that are absent: ``sysDescr``, ``sysName``."""
        out = []
        if not self.sys_descr:
            out.append("sysDescr")
        if not self.sys_name:
            out.append("sysName")
        return tuple(out)


def decode_initiation(body: bytes, *, strict: bool = True, max_tlvs: int = MAX_TLVS) -> Initiation:
    """Decode an Initiation message body (RFC 7854 sections 4.3 and 4.4).

    RFC 7854 section 4.3 says sysDescr and sysName MUST be sent. With ``strict`` a message that
    lacks either raises :class:`BmpError`; without it the gap is reported by
    :attr:`Initiation.missing`. Repeated sysDescr or sysName TLVs are all kept.
    """
    tlvs = decode_tlvs(body, max_tlvs=max_tlvs)
    descr: list[str] = []
    name: list[str] = []
    strings: list[str] = []
    other: list[InfoTlv] = []
    for tlv in tlvs:
        if tlv.type == _INIT_STRING:
            strings.append(_text(tlv.value, strict))
        elif tlv.type == _INIT_SYS_DESCR:
            descr.append(_text(tlv.value, strict))
        elif tlv.type == _INIT_SYS_NAME:
            name.append(_text(tlv.value, strict))
        else:
            other.append(tlv)
    result = Initiation(tlvs, tuple(descr), tuple(name), tuple(strings), tuple(other))
    if strict and result.missing:
        raise BmpError("Initiation lacks the required TLV(s): " + ", ".join(result.missing))
    return result


@dataclass(frozen=True)
class Termination:
    """A Termination message (RFC 7854 section 4.5). ``reason`` is kept as a plain int.

    ``reason`` is ``None`` only when a non-strict decode met a message with no Reason TLV.
    """

    tlvs: tuple[InfoTlv, ...]
    reason: int | None
    strings: tuple[str, ...]
    other: tuple[InfoTlv, ...]

    @property
    def known_reason(self) -> TermReason | None:
        """The :class:`TermReason`, or ``None`` when absent or not one of the five defined."""
        try:
            return None if self.reason is None else TermReason(self.reason)
        except ValueError:
            return None


def decode_termination(
    body: bytes, *, strict: bool = True, max_tlvs: int = MAX_TLVS
) -> Termination:
    """Decode a Termination message body (RFC 7854 section 4.5).

    The Reason TLV (type 1, exactly two octets) is REQUIRED; a Reason of the wrong length is
    always an error, and with ``strict`` a missing or repeated Reason is too. Unknown reason
    codes are returned raw. String TLVs (type 0) are kept in order.
    """
    tlvs = decode_tlvs(body, max_tlvs=max_tlvs)
    reasons: list[int] = []
    strings: list[str] = []
    other: list[InfoTlv] = []
    for tlv in tlvs:
        if tlv.type == _TERM_STRING:
            strings.append(_text(tlv.value, strict))
        elif tlv.type == _TERM_REASON:
            if len(tlv.value) != 2:
                raise BmpError(f"Termination Reason TLV is {len(tlv.value)} octets, not 2")
            reasons.append(int.from_bytes(tlv.value, "big"))
        else:
            other.append(tlv)
    if strict and len(reasons) != 1:
        raise BmpError(
            "Termination lacks the REQUIRED Reason TLV"
            if not reasons
            else "Termination carries more than one Reason TLV"
        )
    return Termination(tlvs, reasons[0] if reasons else None, tuple(strings), tuple(other))


@dataclass(frozen=True)
class PeerUp:
    """A Peer Up message (RFC 7854 section 4.10 with the TLVs of RFC 9736 section 3.3).

    ``sent_open`` and ``received_open`` are whole BGP OPEN messages, header included, undecoded.
    ``local_address`` is ``None`` for the Loc-RIB Instance Peer (RFC 9069 section 5.2).
    """

    local_address: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    local_port: int
    remote_port: int
    sent_open: bytes
    received_open: bytes
    tlvs: tuple[InfoTlv, ...]
    strings: tuple[str, ...]
    vrf_names: tuple[str, ...]
    admin_labels: tuple[str, ...]
    other: tuple[InfoTlv, ...]


def _split_open(raw: bytes, at: int, which: str) -> tuple[bytes, int]:
    """Cut one framed BGP message out of ``raw`` at ``at``: length from the BGP header, no PDU decoding."""
    if len(raw) - at < _BGP_HEADER:
        raise BmpError(f"{which} OPEN message is cut short")
    length = int.from_bytes(raw[at + 16 : at + 18], "big")
    if raw[at + 18] != _BGP_OPEN:
        raise BmpError(f"{which} OPEN message has BGP type {raw[at + 18]}, not OPEN")
    if length < _BGP_HEADER or length > len(raw) - at:
        raise BmpError(f"{which} OPEN message length {length} does not fit")
    return bytes(raw[at : at + length]), at + length


def decode_peer_up(
    body: bytes, peer: PerPeerHeader, *, strict: bool = True, max_tlvs: int = MAX_TLVS
) -> PeerUp:
    """Decode a Peer Up body, the octets after the per-peer header (RFC 7854 section 4.10).

    ``peer`` is the already decoded per-peer header: its V flag says how to read the local
    address. The two OPEN messages are framed by their BGP length field (RFC 4271 section 4.1)
    and returned as bytes. The trailing Information TLVs are OPTIONAL and use the Peer Up
    namespace of RFC 9736 section 3.3; VRF/Table Name must be 1 to 255 octets when ``strict``.
    """
    if len(body) < 20:
        raise BmpError("Peer Up body is shorter than local address and ports")
    local_raw = bytes(body[:16])
    local_port, remote_port = struct.unpack_from(">HH", body, 16)
    local: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    if peer.is_loc_rib:
        local = None
    elif peer.ipv6:
        local = ipaddress.IPv6Address(local_raw)
    else:
        if strict and local_raw[:12] != bytes(12):
            raise BmpError("IPv4 local address is not zero-filled in its twelve leading octets")
        local = ipaddress.IPv4Address(local_raw[12:])
    sent, at = _split_open(body, 20, "sent")
    received, at = _split_open(body, at, "received")
    tlvs = decode_tlvs(body[at:], max_tlvs=max_tlvs)
    strings: list[str] = []
    vrf: list[str] = []
    labels: list[str] = []
    other: list[InfoTlv] = []
    for tlv in tlvs:
        if tlv.type == _UP_STRING:
            strings.append(_text(tlv.value, strict))
        elif tlv.type == _UP_VRF_NAME:
            if strict and not 1 <= len(tlv.value) <= 255:
                raise BmpError("VRF/Table Name TLV must be 1 to 255 octets")
            vrf.append(_text(tlv.value, strict))
        elif tlv.type == _UP_ADMIN_LABEL:
            labels.append(_text(tlv.value, strict))
        else:
            other.append(tlv)
    return PeerUp(
        local,
        local_port,
        remote_port,
        sent,
        received,
        tlvs,
        tuple(strings),
        tuple(vrf),
        tuple(labels),
        tuple(other),
    )


def decode_route_monitoring(raw: bytes, peer: PeerKey) -> Update:
    """Pending behaviour defined by RFC 7854.

    Not implemented yet. See the ``messages.decode_route_monitoring()`` row in
    ROADMAP.md; this stub raises on purpose so nothing downstream mistakes it for working
    code.
    """
    raise NotImplementedError("decode_route_monitoring() is not implemented: RFC 7854")


def decode_statistics(raw: bytes) -> Stats:
    """Pending behaviour defined by RFC 7854.

    Not implemented yet. See the ``messages.decode_statistics()`` row in ROADMAP.md; this
    stub raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("decode_statistics() is not implemented: RFC 7854")
