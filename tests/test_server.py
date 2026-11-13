# ruff: noqa: PT018
"""Connection limits and lifecycle (ROADMAP row ``server.limits``).

RFC 7854 section 3.3 says the router MUST begin with an Initiation message and section 4.1 says
unrecognised message types MUST be ignored; section 3.2 gives the connection-restriction shape
(one per address, a rate) for the router. The numbers and the refusals are library policy. The
messages are hand-built from the common header of section 4.1 and the per-peer header of 4.2.
"""

from __future__ import annotations

import struct

import pytest

from bmpkit.header import MAX_MESSAGE_LENGTH, BmpError, MsgType
from bmpkit.server import Admission, Connection, LimitError, Limits


def msg(kind: int, body: bytes = b"") -> bytes:
    return struct.pack(">BIB", 3, 6 + len(body), kind) + body


def peer_body(address_octet: int, peer_type: int = 0) -> bytes:
    address = bytes(12) + bytes([10, 0, 0, address_octet])
    return struct.pack(">BB8s16sI4sII", peer_type, 0, bytes(8), address, 65001, bytes(4), 0, 0)


INIT = msg(MsgType.INITIATION)


def test_the_first_message_must_be_an_initiation():
    for first in (msg(MsgType.PEER_UP, peer_body(1)), msg(MsgType.ROUTE_MONITORING), msg(99)):
        conn = Connection()
        with pytest.raises(LimitError) as info:
            conn.feed(first)
        assert info.value.limit == "initiation-first" and conn.closed
        with pytest.raises(LimitError) as again:
            conn.feed(INIT)
        assert again.value.limit == "closed"


def test_unknown_types_are_returned_after_initiation_and_bytes_may_arrive_split():
    conn = Connection()
    wire = INIT + msg(99, b"abc") + msg(MsgType.TERMINATION)
    got = []
    for i in range(len(wire)):  # one octet at a time
        got += conn.feed(wire[i : i + 1])
    assert [h.msg_type for h, _ in got] == [4, 99, 5] and got[1][1] == b"abc"
    assert conn.closed  # a Termination ends the connection
    with pytest.raises(LimitError, match="closed"):
        conn.feed(INIT)


def test_a_length_over_the_limit_is_refused_from_the_header_alone():
    conn = Connection(Limits(max_message_length=64))
    conn.feed(INIT)
    huge = struct.pack(">BIB", 3, 65, 0)  # only the six header octets arrive
    with pytest.raises(LimitError) as info:
        conn.feed(huge)
    assert info.value.limit == "message-length"
    assert Limits().max_message_length == MAX_MESSAGE_LENGTH
    other = Connection()
    with pytest.raises(BmpError) as not_limit:
        other.feed(struct.pack(">BIB", 2, 6, 4))  # a version problem is not a limit
    assert not isinstance(not_limit.value, LimitError) and other.closed


def test_peer_up_beyond_max_peers_is_refused_and_peer_down_frees_a_slot():
    conn = Connection(Limits(max_peers=2))
    conn.feed(INIT + msg(MsgType.PEER_UP, peer_body(1)) + msg(MsgType.PEER_UP, peer_body(2)))
    assert len(conn.peers) == 2
    conn.feed(msg(MsgType.PEER_UP, peer_body(1)))  # the same peer again is not a new peer
    assert len(conn.peers) == 2
    conn.feed(msg(MsgType.PEER_DOWN, peer_body(1) + b"\x01"))
    conn.feed(msg(MsgType.PEER_UP, peer_body(3)))
    assert len(conn.peers) == 2
    with pytest.raises(LimitError) as info:
        conn.feed(msg(MsgType.PEER_UP, peer_body(4)))
    assert info.value.limit == "peers"


def test_a_peer_up_without_a_per_peer_header_is_a_decode_error():
    conn = Connection()
    with pytest.raises(BmpError):
        conn.feed(INIT + msg(MsgType.PEER_UP, b"\x00" * 10))


def test_admission_limits_concurrent_connections_per_address():
    adm = Admission(Limits(max_per_address=1, max_connections=100))
    assert adm.admit("192.0.2.1", 0.0)
    assert not adm.admit("192.0.2.1", 1.0)
    assert adm.admit("192.0.2.2", 1.0)  # another address is not affected
    adm.release("192.0.2.1")
    assert adm.admit("192.0.2.1", 2.0)


def test_admission_limits_the_connection_rate_over_a_window():
    adm = Admission(Limits(max_per_address=10, max_connections=2, rate_window=60.0))
    assert adm.admit("a", 0.0) and adm.admit("a", 10.0)
    assert not adm.admit("a", 20.0)  # a refused attempt is not recorded
    assert not adm.admit("a", 59.9)
    assert adm.admit("a", 60.0)  # the first has left the window
    assert not adm.admit("a", 60.1)
