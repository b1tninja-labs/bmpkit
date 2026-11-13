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

BGP PDUs inside messages are kept as bytes in the message objects and decoded by ``pathattr``
(a sibling project, the optional ``codec`` extra): ``decode_route_monitoring`` decodes the UPDATE a
Route Monitoring message carries, ``decode_peer_down`` frames the NOTIFICATION a Peer Down may
carry, ``decode_route_mirroring`` splits the TLVs of a mirror message, and ``add_path_families``
works out which families carry ADD-PATH Path Identifiers from the two OPENs of the Peer Up. The
module imports ``pathattr`` only when one of those is called, so Initiation, Termination and Peer
Up decode without it.
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

__all__ = [
    "MAX_STATS",
    "MAX_TLVS",
    "InfoTlv",
    "Initiation",
    "PeerDown",
    "PeerDownReason",
    "PeerUp",
    "RouteMirroring",
    "RouteMonitoring",
    "Statistic",
    "Statistics",
    "TermReason",
    "Termination",
    "add_path_families",
    "decode_bgp_pdu",
    "decode_initiation",
    "decode_peer_down",
    "decode_peer_up",
    "decode_route_mirroring",
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


class PeerDownReason(enum.IntEnum):
    """Peer Down reason codes: RFC 7854 section 4.9 (1 to 5) and RFC 9069 section 5.3 (6).

    The Reason is one octet. RFC 7854 section 10.8 wrote the registry ranges as 16-bit, which
    verified erratum 7194 corrects to 0 reserved, 1 to 127 Standards Action, 128 to 250
    Specification Required, 251 to 254 experimental and 255 reserved; the IANA registry
    (``bmp-parameters``, updated 2026-05-22) agrees.
    """

    LOCAL_NOTIFICATION = 1
    LOCAL_FSM_EVENT = 2
    REMOTE_NOTIFICATION = 3
    REMOTE_NO_DATA = 4
    DECONFIGURED = 5
    LOCAL_TLV_DATA = 6


@dataclass(frozen=True)
class PeerDown:
    """A Peer Down Notification (RFC 7854 section 4.9; RFC 9069 section 5.3).

    The body this decodes follows the common header *and* the per-peer header, as held erratum
    4830 says the RFC text left unclear. ``reason`` is the raw octet. Depending on it, exactly one
    of ``notification`` (reasons 1 and 3: the whole BGP NOTIFICATION PDU, undecoded),
    ``fsm_event`` (reason 2: the RFC 4271 section 8.1 event code, 0 meaning none defined) or
    ``tlvs`` (reason 6: Information TLVs, with ``vrf_names``) is set; ``extra`` holds data after
    a reason that defines none (4 and 5) and all the octets of an unassigned reason.
    """

    reason: int
    notification: bytes | None
    fsm_event: int | None
    tlvs: tuple[InfoTlv, ...]
    vrf_names: tuple[str, ...]
    extra: bytes

    @property
    def known_reason(self) -> PeerDownReason | None:
        try:
            return PeerDownReason(self.reason)
        except ValueError:
            return None

    @property
    def closed_by_local(self) -> bool | None:
        """True for the local-close reasons, False for remote close, None when unsaid."""
        if self.reason in (1, 2, 6):
            return True
        if self.reason in (3, 4):
            return False
        return None


_BGP_NOTIFICATION = 3


def _split_pdu(raw: bytes, at: int, kind: int, what: str) -> tuple[bytes, int]:
    if len(raw) - at < _BGP_HEADER:
        raise BmpError(f"{what} is cut short")
    length = int.from_bytes(raw[at + 16 : at + 18], "big")
    if raw[at + 18] != kind:
        raise BmpError(f"{what} has BGP type {raw[at + 18]}")
    if length < _BGP_HEADER or length > len(raw) - at:
        raise BmpError(f"{what} length {length} does not fit")
    return bytes(raw[at : at + length]), at + length


def decode_peer_down(body: bytes, *, strict: bool = True, max_tlvs: int = MAX_TLVS) -> PeerDown:
    """Decode a Peer Down body, the octets after the per-peer header (RFC 7854 section 4.9).

    Reasons 1 and 3 carry one BGP NOTIFICATION PDU, framed by its BGP length; reason 2 a two-octet
    FSM event code; reasons 4 and 5 nothing; reason 6 (RFC 9069 section 5.3) Information TLVs,
    where type 3 is the VRF/Table Name. With ``strict`` any octets beyond what the reason
    defines, a PDU that is not a NOTIFICATION, or a bad VRF name raise :class:`BmpError`; without
    it the surplus is kept in ``extra``. An unassigned reason is not an error: its data is
    returned raw (RFC 7854 section 10.8 leaves the space open).
    """
    if not body:
        raise BmpError("Peer Down body has no Reason octet")
    reason, data = body[0], bytes(body[1:])
    notification: bytes | None = None
    fsm: int | None = None
    tlvs: tuple[InfoTlv, ...] = ()
    vrf: list[str] = []
    extra = b""
    if reason in (1, 3):
        notification, at = _split_pdu(data, 0, _BGP_NOTIFICATION, "NOTIFICATION")
        extra = data[at:]
    elif reason == 2:
        if len(data) < 2:
            raise BmpError("FSM Event code is cut short")
        fsm = int.from_bytes(data[:2], "big")
        extra = data[2:]
    elif reason == 6:
        tlvs = decode_tlvs(data, max_tlvs=max_tlvs)
        for tlv in tlvs:
            if tlv.type == _UP_VRF_NAME:
                if strict and not 1 <= len(tlv.value) <= 255:
                    raise BmpError("VRF/Table Name TLV must be 1 to 255 octets")
                vrf.append(_text(tlv.value, strict))
    else:
        extra = data
    if strict and extra and reason in (1, 2, 3, 4, 5):
        raise BmpError(f"Peer Down reason {reason} carries {len(extra)} unexpected octets")
    return PeerDown(reason, notification, fsm, tlvs, tuple(vrf), extra)


def _pathattr() -> Any:
    try:
        import pathattr
    except ImportError as error:  # pragma: no cover - depends on the environment
        raise ImportError(
            "decoding BGP PDUs needs the pathattr package (the 'codec' extra, sibling project)"
        ) from error
    return pathattr


def decode_bgp_pdu(
    pdu: bytes,
    peer: PerPeerHeader,
    *,
    add_path: frozenset[tuple[int, int]] = frozenset(),
    max_length: int = 65535,
    internal: bool = True,
) -> Any:
    """Decode one BGP PDU carried in a BMP message with ``pathattr`` (RFC 7854 sections 4.6, 4.7).

    The AS number width follows the per-peer header: the A flag means 2-octet AS_PATH (RFC 7854
    section 4.2) and the Loc-RIB Instance Peer is always 4-octet (RFC 9069 section 5.4.1).
    ``max_length`` defaults to 65535, because a monitored session may have negotiated extended
    messages (RFC 8654) and BMP does not say. ``internal`` defaults to True so that LOCAL_PREF,
    ORIGINATOR_ID and CLUSTER_LIST are kept and length-checked rather than discarded as RFC 7606
    does for an external neighbour: a post-policy route routinely carries LOCAL_PREF set by
    inbound policy whatever the session type. Raises :class:`BmpError` for what pathattr refuses.
    """
    pa = _pathattr()
    try:
        return pa.decode(
            pdu,
            max_length=max_length,
            four_octet_as=not peer.legacy_as_path,
            internal=internal,
            add_path=add_path,
        )
    except pa.BgpError as error:
        raise BmpError(f"BGP PDU does not decode: {error}") from error


@dataclass(frozen=True)
class RouteMonitoring:
    """A Route Monitoring message (RFC 7854 sections 4.6 and 5).

    ``update`` is the ``pathattr`` UPDATE with its RFC 7606 verdict, ``attributes`` its decoded
    attribute values, ``pdu`` the octets as carried, and ``end_of_rib`` the (AFI, SAFI) this
    UPDATE marks as complete, or None. ``post_policy`` is the per-peer L flag (section 5).
    """

    pdu: bytes
    update: Any
    attributes: Any
    end_of_rib: tuple[int, int] | None
    post_policy: bool


def _end_of_rib(update: Any, attributes: Any) -> tuple[int, int] | None:
    """The family an End-of-RIB UPDATE marks (RFC 7606 section 5.2, describing RFC 4724 section 2).

    An UPDATE with only an empty MP_UNREACH_NLRI is the marker for that family; a completely
    empty UPDATE is the legacy IPv4 unicast marker. RFC 7854 section 5 asks for one per peer, and
    held erratum 7133 points out RFC 4724 defines them per address family, so this reports the
    family and leaves "the peer's dump is complete" to the caller.
    """
    unreach = attributes.mp_unreach
    if unreach is not None and unreach.nlri == () and not update.withdrawn and not update.nlri:
        if len(update.attributes) == 1:
            return (unreach.afi, unreach.safi)
        return None
    if not update.withdrawn and not update.nlri and not update.attributes:
        return (1, 1)
    return None


def decode_route_monitoring(
    body: bytes,
    peer: PerPeerHeader,
    *,
    add_path: frozenset[tuple[int, int]] = frozenset(),
    max_length: int = 65535,
    internal: bool = True,
    budget: Any = None,
) -> RouteMonitoring:
    """Decode a Route Monitoring body, the octets after the per-peer header (RFC 7854 4.6).

    The body is one BGP UPDATE PDU. It is decoded by ``pathattr`` (see :func:`decode_bgp_pdu`)
    and its attributes by ``pathattr.decode_attributes`` with the AS width of the per-peer header
    and ``add_path`` (see :func:`add_path_families`). A PDU that is not an UPDATE raises
    :class:`BmpError`. ``budget`` is an optional ``pathattr.limits.Budget``; an UPDATE over it
    raises :class:`BmpError` rather than being decoded further by the caller.
    """
    pa = _pathattr()
    update = decode_bgp_pdu(body, peer, add_path=add_path, max_length=max_length, internal=internal)
    if not isinstance(update, pa.Update):
        raise BmpError("Route Monitoring carries a BGP message that is not an UPDATE")
    attributes = pa.decode_attributes(
        update.attributes, four_octet_as=not peer.legacy_as_path, add_path=add_path
    )
    if budget is not None:
        try:
            pa.limits.check(pa.message.measure(update, attributes), budget)
        except pa.limits.BudgetExceeded as error:
            raise BmpError(f"UPDATE is over the decoding budget: {error}") from error
    return RouteMonitoring(
        bytes(body), update, attributes, _end_of_rib(update, attributes), peer.post_policy
    )


_MIRROR_BGP_MESSAGE, _MIRROR_INFORMATION = 0, 1


class MirrorInfo(enum.IntEnum):
    """Route Mirroring Information codes, RFC 7854 section 4.7."""

    ERRORED_PDU = 0
    MESSAGES_LOST = 1


@dataclass(frozen=True)
class RouteMirroring:
    """A Route Mirroring message (RFC 7854 sections 4.7 and 6).

    ``bgp_message`` is the verbatim BGP PDU of the BGP Message TLV (type 0), or None; ``info`` the
    Information codes (type 1, two octets each) in order; ``other`` any TLV of another type,
    unread. ``errored`` is true for code 0 (Errored PDU: the message was treated as withdraw per
    RFC 7606) and ``lost`` for code 1 (Messages Lost).
    """

    tlvs: tuple[InfoTlv, ...]
    bgp_message: bytes | None
    info: tuple[int, ...]
    other: tuple[InfoTlv, ...]

    @property
    def errored(self) -> bool:
        return int(MirrorInfo.ERRORED_PDU) in self.info

    @property
    def lost(self) -> bool:
        return int(MirrorInfo.MESSAGES_LOST) in self.info


def decode_route_mirroring(
    body: bytes, *, strict: bool = True, max_tlvs: int = MAX_TLVS
) -> RouteMirroring:
    """Decode a Route Mirroring body, the octets after the per-peer header (RFC 7854 4.7).

    TLVs are a two-octet type, two-octet length and value. The BGP Message TLV (type 0) MUST be
    last if present. An Information TLV (type 1) is two octets. Code 0 (Errored PDU) requires a
    BGP Message TLV in the same message. With ``strict`` a violation, a repeated BGP Message TLV
    or an empty message (RFC 7854: at least one TLV SHOULD be included) raises
    :class:`BmpError`. An Information code outside 0 and 1 is kept in ``info``; any other TLV type
    goes to ``other``.
    """
    tlvs = decode_tlvs(body, max_tlvs=max_tlvs)
    message: bytes | None = None
    info: list[int] = []
    other: list[InfoTlv] = []
    for index, tlv in enumerate(tlvs):
        if tlv.type == _MIRROR_BGP_MESSAGE:
            if strict and (message is not None or index != len(tlvs) - 1):
                raise BmpError("the BGP Message TLV must occur once and last")
            message = tlv.value if message is None else message
        elif tlv.type == _MIRROR_INFORMATION:
            if len(tlv.value) != 2:
                raise BmpError(f"Information TLV is {len(tlv.value)} octets, not 2")
            info.append(int.from_bytes(tlv.value, "big"))
        else:
            other.append(tlv)
    if strict and not tlvs:
        raise BmpError("Route Mirroring message carries no TLV")
    if strict and MirrorInfo.ERRORED_PDU in info and message is None:
        raise BmpError("Errored PDU information without a BGP Message TLV")
    return RouteMirroring(tlvs, message, tuple(info), tuple(other))


def add_path_families(up: PeerUp, peer: PerPeerHeader) -> frozenset[tuple[int, int]]:
    """The <AFI, SAFI> pairs whose NLRI carry Path Identifiers in this peer's route messages.

    Worked out from the two OPEN messages of the Peer Up with ``pathattr.addpath`` (RFC 7911
    section 5). Adj-RIB-In (O flag clear) carries what the monitored router *received*: it
    advertised Receive and the peer Send. Adj-RIB-Out (O flag set, RFC 8671) carries what it
    *sent*: it advertised Send and the peer Receive. That reading of RFC 8671 is an inference,
    since neither RFC 8671 nor RFC 7854 mentions ADD-PATH; check it against a capture. For the
    Loc-RIB Instance Peer, RFC 9069 section 5.2 says the presence of the capability in the
    fabricated OPEN means additional paths are used whatever its mode, so every family it lists
    counts.
    """
    pa = _pathattr()
    try:
        sent = pa.decode(up.sent_open)
        received = pa.decode(up.received_open)
    except pa.BgpError as error:
        raise BmpError(f"Peer Up OPEN does not decode: {error}") from error
    if not isinstance(sent, pa.Open) or not isinstance(received, pa.Open):
        raise BmpError("Peer Up carries a BGP message that is not an OPEN")
    if peer.is_loc_rib:
        fams: set[tuple[int, int]] = set()
        for capability in sent.capabilities:
            if capability.code == pa.addpath.ADD_PATH_CAPABILITY:
                fams.update((f.afi, f.safi) for f in pa.addpath.parse_capability(capability.value))
        return frozenset(fams)
    if peer.adj_rib_out:
        return pa.addpath.send_families(sent, received)
    return pa.addpath.receive_families(sent, received)


_COUNTER32 = frozenset({0, 1, 2, 3, 4, 5, 6, 11, 12, 13})  # RFC 7854 section 4.8
_GAUGE64 = frozenset({7, 8, 14, 15, 18, 20, 29, 31, 33, 39})  # RFC 7854, RFC 8671, RFC 9972
_AFI_SAFI_GAUGE64 = frozenset(
    {9, 10, 16, 17, 19, 21, 22, 23, 26, 27, 28, 30, 32, 34, 35, 36, 37, 38, 40, 41, 42, 43}
)
_RFC9972_TYPES = range(18, 44)
MAX_STATS = 4096


@dataclass(frozen=True)
class Statistic:
    """One Stat TLV (RFC 7854 section 4.8): its type, the value, and the octets it came from.

    ``kind`` is ``"counter32"`` (a 32-bit counter), ``"gauge64"`` (a 64-bit gauge),
    ``"afi-safi-gauge64"`` (2-octet AFI, 1-octet SAFI, 64-bit gauge; ``afi`` and ``safi`` set) or
    ``"unknown"`` for a type this module does not define, or a defined one whose length is wrong
    when read without ``strict``; then ``value`` is None and ``raw`` is all there is.
    """

    type: int
    kind: str
    value: int | None
    raw: bytes
    afi: int | None = None
    safi: int | None = None


@dataclass(frozen=True)
class Statistics:
    """A Statistics Report body: the counters in the order sent."""

    items: tuple[Statistic, ...]

    def get(self, stat_type: int, afi: int | None = None, safi: int | None = None) -> int | None:
        """The value of the first statistic of that type (and family), or None."""
        for item in self.items:
            if item.type == stat_type and item.afi == afi and item.safi == safi:
                return item.value
        return None


def decode_statistics(raw: bytes, *, strict: bool = True, max_stats: int = MAX_STATS) -> Statistics:
    """Decode a Statistics Report body, the octets after the per-peer header (RFC 7854 section 4.8).

    A 4-octet Stats Count then that many TLVs (2-octet type, 2-octet length, data). Types 0 to 6, 11
    to 13 are 32-bit counters; 7, 8 and the others listed in RFC 8671 table 2 and RFC 9972 are 64-bit
    gauges, per-AFI/SAFI ones (9, 10, 16, 17 and RFC 9972's) carrying a 2-octet AFI and a 1-octet
    SAFI first (11 octets); RFC 9972 section 3.1 fixes the length at 8 or 11. An unrecognised type
    is kept with ``kind="unknown"`` (a receiver "MUST ignore" it, not lose it). With ``strict``
    these raise :class:`BmpError`: a known type of the wrong length, a Stats Count that disagrees
    with the TLVs or is zero (section 4.8: "at least one statistic MUST be carried"), more than
    ``max_stats`` TLVs, and, for RFC 9972's types 18 to 43, a repeated global statistic or a repeated
    (type, AFI, SAFI) (RFC 9972 section 3.1). Without it the defect is kept as an unknown item or
    ignored. RFC 7854 section 4.8 also says unexpected data in Stat Data is ignored; the octets stay
    in ``raw``.
    """
    if len(raw) < 4:
        raise BmpError("Statistics Report is shorter than its Stats Count")
    count = int.from_bytes(raw[:4], "big")
    if count > max_stats:
        raise BmpError(f"Statistics Report claims {count} statistics; the limit is {max_stats}")
    if strict and count == 0:
        raise BmpError("a Statistics Report carries at least one statistic (RFC 7854 section 4.8)")
    items: list[Statistic] = []
    seen: set[tuple[int, int | None, int | None]] = set()
    at = 4
    for _ in range(count):
        if at + 4 > len(raw):
            raise BmpError("Statistics Report is cut short in a Stat header")
        stat_type, length = struct.unpack_from(">HH", raw, at)
        at += 4
        if at + length > len(raw):
            raise BmpError(f"Stat type {stat_type} runs past the end of the report")
        data = bytes(raw[at : at + length])
        at += length
        item = _statistic(stat_type, data, strict)
        if strict and stat_type in _RFC9972_TYPES and item.kind != "unknown":
            key = (stat_type, item.afi, item.safi)
            if key in seen:
                raise BmpError(f"Stat type {stat_type} appears twice for one scope")
            seen.add(key)
        items.append(item)
    if strict and at != len(raw):
        raise BmpError(f"{len(raw) - at} octets follow the {count} statistics of the report")
    return Statistics(tuple(items))


def _statistic(stat_type: int, data: bytes, strict: bool) -> Statistic:
    if stat_type in _COUNTER32:
        kind, size = "counter32", 4
    elif stat_type in _GAUGE64:
        kind, size = "gauge64", 8
    elif stat_type in _AFI_SAFI_GAUGE64:
        kind, size = "afi-safi-gauge64", 11
    else:
        return Statistic(stat_type, "unknown", None, data)
    if len(data) != size:
        if strict:
            raise BmpError(f"Stat type {stat_type} is {len(data)} octets; {kind} needs {size}")
        return Statistic(stat_type, "unknown", None, data)
    if kind == "afi-safi-gauge64":
        afi, safi = struct.unpack(">HB", data[:3])
        return Statistic(stat_type, kind, int.from_bytes(data[3:], "big"), data, afi, safi)
    return Statistic(stat_type, kind, int.from_bytes(data, "big"), data)
