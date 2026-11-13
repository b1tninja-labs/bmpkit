# ruff: noqa: PT018
"""BMP messages as bgpfeed events (ROADMAP row ``events.bgpfeed-event``).

Vectors are hand-built from RFC 7854 sections 4.2, 4.6 and 4.9, RFC 8671 section 4 and RFC 9069
section 4; the RFCs carry no byte examples, so these pin the reading of the text.
"""

from __future__ import annotations

import datetime
import ipaddress
import struct

import pytest
from bgpfeed.model import EventKind, RibView, SessionState

from bmpkit.events import (
    peer_down_event,
    peer_of,
    peer_up_event,
    route_monitoring_events,
    view_of_header,
)
from bmpkit.header import BmpError, PerPeerHeader, decode_per_peer
from bmpkit.messages import decode_peer_down, decode_route_monitoring

MARKER = b"\xff" * 16


def bgp(kind: int, body: bytes) -> bytes:
    return MARKER + struct.pack(">HB", 19 + len(body), kind) + body


def attr(flags: int, code: int, value: bytes) -> bytes:
    return bytes([flags, code, len(value)]) + value


def update(withdrawn: bytes = b"", attrs: bytes = b"", nlri: bytes = b"") -> bytes:
    body = struct.pack(">H", len(withdrawn)) + withdrawn + struct.pack(">H", len(attrs))
    return bgp(2, body + attrs + nlri)


ORIGIN = attr(0x40, 1, b"\x00")
AS_PATH_VALUE = bytes([2, 2]) + struct.pack(">II", 65000, 196618)
AS_PATH4 = attr(0x40, 2, AS_PATH_VALUE)
NEXT_HOP = attr(0x40, 3, bytes([192, 0, 2, 1]))
GOOD = ORIGIN + AS_PATH4 + NEXT_HOP
NLRI_24 = bytes([24, 192, 0, 2])
WITHDRAWN_24 = bytes([24, 198, 51, 100])


def header(
    peer_type: int = 0, flags: int = 0, seconds: int = 0, micros: int = 0, distinguisher=bytes(8)
) -> PerPeerHeader:
    raw = struct.pack(
        ">BB8s16sI4sII", peer_type, flags, distinguisher,
        bytes(12) + bytes([10, 0, 0, 1]), 65001, bytes([10, 0, 0, 9]), seconds, micros,
    )  # fmt: skip
    return decode_per_peer(raw)


def loc_rib_header(flags: int = 0) -> PerPeerHeader:
    raw = struct.pack(
        ">BB8s16sI4sII", 3, flags, bytes(8), bytes(16), 65001, bytes([10, 0, 0, 9]), 0, 0
    )
    return decode_per_peer(raw)


def events(pdu: bytes, ph: PerPeerHeader):
    return list(route_monitoring_events(decode_route_monitoring(pdu, ph), ph, source="bmp:r1"))


def test_route_monitoring_events():
    ph = header(seconds=1_700_000_000, micros=250_000, distinguisher=bytes(range(8)))
    got = events(update(WITHDRAWN_24, GOOD, NLRI_24), ph)
    assert [e.kind for e in got] == [EventKind.WITHDRAW, EventKind.ANNOUNCE]
    withdraw, announce = got
    assert withdraw.prefix == ipaddress.ip_network("198.51.100.0/24")
    assert announce.prefix == ipaddress.ip_network("192.0.2.0/24")
    assert withdraw.as_path is None and announce.as_path == AS_PATH_VALUE
    assert announce.time == datetime.datetime(
        2023, 11, 14, 22, 13, 20, 250_000, tzinfo=datetime.UTC
    )
    assert announce.source == "bmp:r1" and announce.four_octet_as is True
    assert announce.peer.address == ipaddress.ip_address("10.0.0.1") and announce.peer.asn == 65001
    assert announce.peer.distinguisher == bytes(range(8))
    assert announce.peer.bgp_id == ipaddress.IPv4Address("10.0.0.9")
    assert announce.view is RibView.ADJ_RIB_IN_PRE


def test_a_zero_timestamp_gives_an_event_without_time():
    (event,) = events(update(attrs=GOOD, nlri=NLRI_24), header())
    assert event.time is None


@pytest.mark.parametrize(
    ("flags", "view"),
    [
        (0x00, RibView.ADJ_RIB_IN_PRE),
        (0x40, RibView.ADJ_RIB_IN_POST),
        (0x10, RibView.ADJ_RIB_OUT_PRE),
        (0x50, RibView.ADJ_RIB_OUT_POST),
    ],
)
def test_the_l_and_o_flags_select_the_view(flags, view):
    assert view_of_header(header(flags=flags)) is view


def test_the_loc_rib_instance_peer_has_no_address_and_its_own_view():
    ph = loc_rib_header(flags=0x80)  # the F flag must not be read as V
    assert view_of_header(ph) is RibView.LOC_RIB
    assert peer_of(ph).address is None
    (event,) = events(update(attrs=GOOD, nlri=NLRI_24), ph)
    assert event.view is RibView.LOC_RIB and event.peer.address is None and event.four_octet_as


def test_the_a_flag_sets_the_as_width():
    ph = header(flags=0x20)
    as2 = attr(0x40, 2, bytes([2, 2]) + struct.pack(">HH", 65000, 65001))
    (event,) = events(update(attrs=ORIGIN + as2 + NEXT_HOP, nlri=NLRI_24), ph)
    assert event.four_octet_as is False and event.as_path == bytes([2, 2]) + struct.pack(
        ">HH", 65000, 65001
    )


def test_mp_reach_and_mp_unreach_give_events():
    reach = attr(0x80, 14, struct.pack(">HBB", 2, 1, 16) + bytes([0x20, 1]) + bytes(14) + b"\x00"
                 + bytes([32, 0x20, 0x01, 0x0D, 0xB8]))  # fmt: skip
    unreach = attr(0x80, 15, struct.pack(">HB", 2, 1) + bytes([32, 0x20, 0x01, 0x0D, 0xB9]))
    got = events(update(attrs=ORIGIN + AS_PATH4 + reach + unreach), header())
    assert [(e.kind, str(e.prefix)) for e in got] == [
        (EventKind.WITHDRAW, "2001:db9::/32"),
        (EventKind.ANNOUNCE, "2001:db8::/32"),
    ]


def test_end_of_rib_gives_no_event():
    assert events(update(), header()) == []


def test_treat_as_withdraw_turns_announcements_into_withdrawals():
    bad_origin = attr(0x40, 1, b"\x09")  # an undefined ORIGIN value: RFC 7606 section 7.1
    got = events(update(attrs=bad_origin + AS_PATH4 + NEXT_HOP, nlri=NLRI_24), header())
    assert [(e.kind, e.reason, e.as_path) for e in got] == [
        (EventKind.WITHDRAW, "treat-as-withdraw", None)
    ]


def test_an_untrusted_update_is_refused():
    # an IPv6 next hop of 5 octets: pathattr asks for the AFI/SAFI to be disabled (RFC 7606 7.11)
    reach = attr(
        0x80, 14, struct.pack(">HBB", 2, 1, 5) + bytes(5) + b"\x00" + bytes([32, 0x20, 1, 13, 0xB8])
    )
    ph = header()
    message = decode_route_monitoring(update(attrs=ORIGIN + AS_PATH4 + reach), ph)
    assert message.update.action.name == "AFI_SAFI_DISABLE"
    with pytest.raises(BmpError, match="not trusted"):
        list(route_monitoring_events(message, ph, source="s"))


def test_peer_down_and_up_events_carry_a_session_state_and_no_fsm_numbers():
    ph = header(seconds=1_700_000_000)
    notification = bgp(3, bytes([6, 2]))
    down = peer_down_event(decode_peer_down(bytes([3]) + notification), ph, source="bmp:r1")
    assert down.kind is EventKind.PEER_STATE and down.session is SessionState.DOWN
    assert (
        down.reason == "remote-notification" and down.old_state is None and down.new_state is None
    )
    assert down.time is not None and down.view is None
    unassigned = peer_down_event(decode_peer_down(bytes([200])), ph, source="s")
    assert unassigned.reason == "reason-200"

    class _Up:  # peer_up_event reads nothing from the message
        pass

    up = peer_up_event(_Up(), header(), source="bmp:r1")
    assert up.session is SessionState.UP and up.time is None and up.peer.asn == 65001
