# ruff: noqa: PT018
"""Peer Down, Route Monitoring and Route Mirroring bodies, with the BGP PDUs decoded by pathattr.

Vectors are hand-built from RFC 7854 sections 4.6, 4.7, 4.9 and 5, RFC 9069 section 5 and the
pathattr wire formats; the RFCs carry no byte examples, so these pin the reading of the text and
not interoperability (ROADMAP row ``header.capture-fixtures``).
"""

from __future__ import annotations

import ipaddress
import struct

import pathattr
import pytest

from bmpkit.header import BmpError, PerPeerHeader, decode_common, decode_per_peer, frame
from bmpkit.messages import (
    InfoTlv,
    PeerDownReason,
    PeerUp,
    add_path_families,
    decode_peer_down,
    decode_route_mirroring,
    decode_route_monitoring,
)
from bmpkit.mirror import decode_mirrored, extract_bgp_message

MARKER = b"\xff" * 16


def bgp(kind: int, body: bytes) -> bytes:
    return MARKER + struct.pack(">HB", 19 + len(body), kind) + body


def attr(flags: int, code: int, value: bytes) -> bytes:
    return bytes([flags, code, len(value)]) + value


def update(withdrawn: bytes = b"", attrs: bytes = b"", nlri: bytes = b"") -> bytes:
    body = struct.pack(">H", len(withdrawn)) + withdrawn + struct.pack(">H", len(attrs))
    return bgp(2, body + attrs + nlri)


ORIGIN = attr(0x40, 1, b"\x00")
AS_PATH4 = attr(0x40, 2, bytes([2, 2]) + struct.pack(">II", 65000, 196618))
AS_PATH2 = attr(0x40, 2, bytes([2, 2]) + struct.pack(">HH", 65000, 65001))
NEXT_HOP = attr(0x40, 3, bytes([192, 0, 2, 1]))
LOCAL_PREF = attr(0x40, 5, struct.pack(">I", 200))
NLRI_24 = bytes([24, 192, 0, 2])


def peer(peer_type: int = 0, flags: int = 0) -> PerPeerHeader:
    return PerPeerHeader(
        peer_type, flags, bytes(8), ipaddress.IPv4Address("10.0.0.1"), 65001,
        ipaddress.IPv4Address("10.0.0.1"), (0, 0),
    )  # fmt: skip


def per_peer_wire(peer_type: int = 0, flags: int = 0) -> bytes:
    addr = bytes(12) + bytes([10, 0, 0, 1])
    return struct.pack(">BB8s16sI4sII", peer_type, flags, bytes(8), addr, 65001,
                       bytes([10, 0, 0, 1]), 0, 0)  # fmt: skip


# ---- Peer Down (RFC 7854 section 4.9, erratum 4830, RFC 9069 section 5.3) -----------------


def notification(code: int = 6, sub: int = 2) -> bytes:
    return bgp(3, bytes([code, sub]))


def test_peer_down_body_follows_common_and_per_peer_header_erratum_4830():
    body = bytes([3]) + notification()
    wire = struct.pack(">BIB", 3, 6 + 42 + len(body), 2) + per_peer_wire() + body
    header, rest = frame(wire)
    assert header.msg_type == 2
    ph = decode_per_peer(rest[:42])
    down = decode_peer_down(rest[42:])
    assert ph.asn == 65001
    assert down.reason == PeerDownReason.REMOTE_NOTIFICATION
    assert down.notification == notification()
    assert down.closed_by_local is False
    assert decode_common(wire).length == len(wire)


@pytest.mark.parametrize(
    ("body", "reason", "closed_local"),
    [
        (bytes([1]) + notification(4, 0), 1, True),
        (bytes([2, 0, 7]), 2, True),
        (bytes([2, 0, 0]), 2, True),
        (bytes([4]), 4, False),
        (bytes([5]), 5, None),
    ],
)
def test_peer_down_each_defined_reason(body, reason, closed_local):
    down = decode_peer_down(body)
    assert down.reason == reason and down.closed_by_local is closed_local
    assert down.known_reason is not None
    if reason == 2:
        assert down.fsm_event == body[2]
    else:
        assert down.fsm_event is None


def test_peer_down_reason_six_carries_a_vrf_name_tlv_rfc_9069():
    tlv = struct.pack(">HH", 3, 6) + b"vrf-a1"
    down = decode_peer_down(bytes([6]) + tlv)
    assert down.known_reason is PeerDownReason.LOCAL_TLV_DATA
    assert down.vrf_names == ("vrf-a1",) and down.tlvs == (InfoTlv(3, b"vrf-a1"),)
    with pytest.raises(BmpError):
        decode_peer_down(bytes([6]) + struct.pack(">HH", 3, 0))


def test_peer_down_unassigned_reason_keeps_its_octets():
    down = decode_peer_down(bytes([200, 1, 2, 3]))
    assert down.known_reason is None and down.extra == bytes([1, 2, 3])
    assert decode_peer_down(bytes([0])).known_reason is None  # 0 is Reserved


@pytest.mark.parametrize(
    "body",
    [
        b"",
        bytes([2, 0]),
        bytes([1]),
        bytes([1]) + bgp(1, bytes(10)),
        bytes([4, 9]),
        bytes([1]) + notification() + b"x",
    ],
    ids=[
        "empty",
        "short-fsm",
        "no-pdu",
        "not-notification",
        "surplus-after-4",
        "surplus-after-pdu",
    ],
)
def test_peer_down_malformed_is_refused_when_strict(body):
    with pytest.raises(BmpError):
        decode_peer_down(body)


def test_peer_down_lenient_keeps_surplus():
    assert decode_peer_down(bytes([4, 9]), strict=False).extra == b"\x09"


# ---- Route Monitoring (RFC 7854 sections 4.6 and 5) ----------------------------------------


def test_route_monitoring_decodes_the_update_with_pathattr():
    pdu = update(attrs=ORIGIN + AS_PATH4 + NEXT_HOP + LOCAL_PREF, nlri=NLRI_24)
    got = decode_route_monitoring(pdu, peer())
    assert [str(n) for n in got.update.nlri] == ["192.0.2.0/24"]
    assert got.attributes.as_path[0].asns == (65000, 196618)
    assert got.attributes.local_pref == 200  # kept, not discarded as for an external neighbour
    assert got.update.action is pathattr.Action.NONE
    assert got.pdu == pdu and got.end_of_rib is None and got.post_policy is False


def test_route_monitoring_l_flag_and_a_flag_come_from_the_per_peer_header():
    pdu = update(attrs=ORIGIN + AS_PATH2 + NEXT_HOP, nlri=NLRI_24)
    got = decode_route_monitoring(pdu, peer(flags=0x40 | 0x20))
    assert got.post_policy is True
    assert got.attributes.as_path[0].asns == (65000, 65001)  # A flag: 2-octet AS_PATH
    # The same octets read as 4-octet AS numbers are malformed: treat-as-withdraw.
    wrong = decode_route_monitoring(pdu, peer())
    assert wrong.update.action is pathattr.Action.TREAT_AS_WITHDRAW


def test_route_monitoring_end_of_rib_markers():
    assert decode_route_monitoring(update(), peer()).end_of_rib == (1, 1)
    unreach = attr(0x80, 15, struct.pack(">HB", 2, 1))
    assert decode_route_monitoring(update(attrs=unreach), peer()).end_of_rib == (2, 1)
    # A withdrawal of a real prefix is not a marker.
    withdrawing = attr(0x80, 15, struct.pack(">HB", 2, 1) + bytes([32, 0x20, 1, 13, 0xB8]))
    assert decode_route_monitoring(update(attrs=withdrawing), peer()).end_of_rib is None
    assert (
        decode_route_monitoring(update(withdrawn=bytes([24, 192, 0, 2])), peer()).end_of_rib is None
    )


def test_route_monitoring_refuses_non_update_and_garbage():
    with pytest.raises(BmpError):
        decode_route_monitoring(bgp(4, b""), peer())
    with pytest.raises(BmpError):
        decode_route_monitoring(b"\x00" * 30, peer())


def test_route_monitoring_budget_refuses_an_oversized_update():
    pdu = update(attrs=ORIGIN + AS_PATH4 + NEXT_HOP, nlri=NLRI_24 * 5)
    decode_route_monitoring(pdu, peer(), budget=pathattr.limits.Budget(nlri=5))
    with pytest.raises(BmpError, match="budget"):
        decode_route_monitoring(pdu, peer(), budget=pathattr.limits.Budget(nlri=4))


def sessions_peer_up(sent_caps: list[tuple[int, bytes]], received_caps: list[tuple[int, bytes]]):
    def opened(caps):
        params = tuple(
            pathattr.message.OptionalParameter(2, bytes([code, len(value)]) + value)
            for code, value in caps
        )
        return pathattr.encode(
            pathattr.Open(4, 65001, 90, ipaddress.IPv4Address("10.0.0.1"), params)
        )

    return PeerUp(
        ipaddress.IPv4Address("10.0.0.2"), 179, 40000,
        opened(sent_caps), opened(received_caps), (), (), (), (), (),
    )  # fmt: skip


ADD_PATH_BOTH = (69, struct.pack(">HBB", 1, 1, 3))
ADD_PATH_SEND = (69, struct.pack(">HBB", 1, 1, 2))
ADD_PATH_RECV = (69, struct.pack(">HBB", 1, 1, 1))


def test_add_path_families_follow_the_direction_of_the_rib():
    up = sessions_peer_up([ADD_PATH_RECV], [ADD_PATH_SEND])
    assert add_path_families(up, peer()) == {(1, 1)}  # Adj-RIB-In: we receive, they send
    assert add_path_families(up, peer(flags=0x10)) == frozenset()  # Adj-RIB-Out: we do not send
    out = sessions_peer_up([ADD_PATH_SEND], [ADD_PATH_RECV])
    assert add_path_families(out, peer(flags=0x10)) == {(1, 1)}
    assert add_path_families(out, peer()) == frozenset()


def test_add_path_families_loc_rib_counts_any_listed_family_rfc_9069_5_2():
    up = sessions_peer_up([ADD_PATH_SEND], [ADD_PATH_SEND])
    loc = PerPeerHeader(3, 0, bytes(8), None, 65001, ipaddress.IPv4Address("10.0.0.1"), (0, 0))
    assert add_path_families(up, loc) == {(1, 1)}


def test_route_monitoring_with_add_path_reads_path_identifiers():
    up = sessions_peer_up([ADD_PATH_RECV], [ADD_PATH_SEND])
    families = add_path_families(up, peer())
    pdu = update(attrs=ORIGIN + AS_PATH4 + NEXT_HOP, nlri=struct.pack(">I", 9) + NLRI_24)
    got = decode_route_monitoring(pdu, peer(), add_path=families)
    assert got.update.nlri_path_ids == (9,)
    assert [str(n) for n in got.update.nlri] == ["192.0.2.0/24"]


def test_add_path_families_refuses_garbage_opens():
    bad = PeerUp(None, 0, 0, b"x" * 29, b"x" * 29, (), (), (), (), ())
    with pytest.raises(BmpError):
        add_path_families(bad, peer())


# ---- Route Mirroring (RFC 7854 sections 4.7 and 6) -----------------------------------------


def mtlv(kind: int, value: bytes) -> bytes:
    return struct.pack(">HH", kind, len(value)) + value


def test_route_mirroring_splits_information_and_bgp_message():
    pdu = update(attrs=ORIGIN + AS_PATH4 + NEXT_HOP, nlri=NLRI_24)
    body = mtlv(1, b"\x00\x00") + mtlv(0, pdu)
    got = decode_route_mirroring(body)
    assert got.errored and not got.lost and got.info == (0,)
    assert extract_bgp_message(got) == pdu
    decoded = decode_mirrored(got, peer())
    assert [str(n) for n in decoded.nlri] == ["192.0.2.0/24"]


def test_route_mirroring_messages_lost_has_no_pdu():
    got = decode_route_mirroring(mtlv(1, b"\x00\x01"))
    assert got.lost and got.bgp_message is None
    with pytest.raises(BmpError):
        extract_bgp_message(got)


@pytest.mark.parametrize(
    "body",
    [
        b"",
        mtlv(0, update()) + mtlv(1, b"\x00\x01"),
        mtlv(0, update()) + mtlv(0, update()),
        mtlv(1, b"\x00\x00"),
        mtlv(1, b"\x00"),
    ],
    ids=["empty", "bgp-message-not-last", "two-bgp-messages", "errored-without-pdu", "short-info"],
)
def test_route_mirroring_violations_are_refused_when_strict(body):
    with pytest.raises(BmpError):
        decode_route_mirroring(body)


def test_route_mirroring_unknown_tlv_and_code_are_kept():
    got = decode_route_mirroring(mtlv(7, b"zz") + mtlv(1, b"\x00\x09") + mtlv(0, update()))
    assert got.other == (InfoTlv(7, b"zz"),) and got.info == (9,)
    assert not got.errored and not got.lost


def test_route_mirroring_errored_pdu_may_not_decode_but_stays_available():
    garbage = bgp(2, b"\x00\x00\x00\x09" + b"\x00" * 3)  # attribute length overruns the message
    got = decode_route_mirroring(mtlv(1, b"\x00\x00") + mtlv(0, garbage))
    assert extract_bgp_message(got) == garbage
    with pytest.raises(BmpError):
        decode_mirrored(got, peer())
