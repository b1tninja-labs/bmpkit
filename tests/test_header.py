"""Common and per-peer header decoding.

Vectors: RFC 7854 has no byte examples, so every vector here is built by hand from the figures
and field lists of RFC 7854 sections 4.1 and 4.2, RFC 8671 section 4 and RFC 9069 sections 4
and 5.1 (read through rfclib on 2026-11-13). A capture from FRR or BIRD is a ROADMAP row.
"""

from __future__ import annotations

import datetime
import ipaddress
import struct

import pytest

from bmpkit.header import (
    BmpError,
    MsgType,
    PeerType,
    decode_common,
    decode_per_peer,
    frame,
)


def common(version: int = 3, length: int = 6, msg_type: int = 0) -> bytes:
    return struct.pack(">BIB", version, length, msg_type)


def per_peer(
    peer_type: int = 0,
    flags: int = 0,
    dist: bytes = bytes(8),
    addr: bytes = bytes(12) + bytes([192, 0, 2, 1]),
    asn: int = 65001,
    bgp_id: bytes = bytes([10, 0, 0, 1]),
    sec: int = 0,
    usec: int = 0,
) -> bytes:
    return struct.pack(">BB8s16sI4sII", peer_type, flags, dist, addr, asn, bgp_id, sec, usec)


def test_common_header_version3_route_monitoring():
    header = decode_common(common(3, 100, 0))
    assert (header.version, header.length, header.msg_type) == (3, 100, 0)
    assert header.known_type is MsgType.ROUTE_MONITORING


@pytest.mark.parametrize("code", range(7))
def test_every_defined_message_type_is_known(code):
    assert decode_common(common(msg_type=code)).known_type == MsgType(code)


@pytest.mark.parametrize("version", [0, 1, 2, 4, 255])
def test_common_header_rejects_version_0_1_2_4(version):
    with pytest.raises(BmpError, match="unsupported BMP version"):
        decode_common(common(version=version))


@pytest.mark.parametrize("code", [7, 100, 255])
def test_common_header_unknown_type_is_returned_not_error(code):
    header = decode_common(common(msg_type=code))
    assert header.msg_type == code
    assert header.known_type is None


@pytest.mark.parametrize("length", [0, 1, 5])
def test_common_header_length_less_than_6_rejected(length):
    with pytest.raises(BmpError, match="shorter than the common header"):
        decode_common(common(length=length))


@pytest.mark.parametrize("size", range(6))
def test_common_header_short_input_rejected(size):
    with pytest.raises(BmpError, match="needs 6 octets"):
        decode_common(common()[:size])


def test_common_header_giant_length_refused_by_default_and_allowed_when_asked():
    with pytest.raises(BmpError, match="exceeds the limit"):
        decode_common(common(length=0xFFFFFFFF))
    assert decode_common(common(length=0xFFFFFFFF), max_length=None).length == 0xFFFFFFFF


def test_decode_common_never_reads_past_the_header():
    # the length field claims a long message; decode_common alone does not need the body
    assert decode_common(common(length=1000) + b"").length == 1000
    header = decode_common(common(length=7, msg_type=4) + b"x" * 500)
    assert header.length == 7


def test_decode_common_accepts_bytes_memoryview_bytearray():
    raw = common(3, 6, 5)
    expected = decode_common(raw)
    assert decode_common(bytearray(raw)) == expected
    assert decode_common(memoryview(raw)) == expected


def test_frame_returns_exactly_length_octets_of_message():
    raw = common(3, 9, 4) + b"abc" + b"NEXT MESSAGE"
    header, body = frame(raw)
    assert header.length == 9
    assert body == b"abc"


def test_frame_refuses_a_message_cut_short():
    with pytest.raises(BmpError, match="length field says"):
        frame(common(3, 20, 4) + b"abc")


def test_per_peer_ipv4_zero_filled_prefix():
    header = decode_per_peer(per_peer())
    assert header.address == ipaddress.IPv4Address("192.0.2.1")
    assert header.bgp_id == ipaddress.IPv4Address("10.0.0.1")
    assert header.peer_type == PeerType.GLOBAL
    assert not header.ipv6


def test_per_peer_ipv4_nonzero_fill_refused_strict_accepted_lenient():
    raw = per_peer(addr=bytes([1]) + bytes(11) + bytes([192, 0, 2, 1]))
    with pytest.raises(BmpError, match="zero-filled"):
        decode_per_peer(raw)
    assert decode_per_peer(raw, strict=False).address == ipaddress.IPv4Address("192.0.2.1")


def test_per_peer_ipv6():
    addr = ipaddress.IPv6Address("2001:db8::1").packed
    header = decode_per_peer(per_peer(flags=0x80, addr=addr))
    assert header.ipv6
    assert header.address == ipaddress.IPv6Address("2001:db8::1")


def test_per_peer_flags_ignore_reserved_bits():
    # V L A O are bits 0..3 (0x80 0x40 0x20 0x10); the low four bits are reserved and ignored.
    base = decode_per_peer(per_peer(flags=0x00))
    noisy = decode_per_peer(per_peer(flags=0x0F))
    assert noisy.address == base.address
    assert (noisy.ipv6, noisy.post_policy, noisy.legacy_as_path, noisy.adj_rib_out) == (False,) * 4
    assert decode_per_peer(per_peer(flags=0x40 | 0x0F)).post_policy


def test_per_peer_flag_bits_individually():
    assert decode_per_peer(per_peer(flags=0x40)).post_policy
    assert decode_per_peer(per_peer(flags=0x20)).legacy_as_path
    only = decode_per_peer(per_peer(flags=0x20))
    assert (only.post_policy, only.adj_rib_out, only.ipv6) == (False, False, False)


def test_per_peer_o_flag_adj_rib_out():
    # RFC 8671 section 4: |V|L|A|O| Resv |
    assert decode_per_peer(per_peer(flags=0x10)).adj_rib_out
    assert not decode_per_peer(per_peer(flags=0x00)).adj_rib_out


def test_per_peer_loc_rib_type3_f_flag_and_zero_address():
    # RFC 9069 section 4.2: the F flag is the 0x80 bit, which V would use for types 0 to 2.
    zero = bytes(16)
    header = decode_per_peer(per_peer(peer_type=3, flags=0x80, addr=zero))
    assert header.is_loc_rib
    assert header.loc_rib_filtered
    assert not header.ipv6  # the bit is F here, not V
    assert header.address is None
    unfiltered = decode_per_peer(per_peer(peer_type=3, flags=0x00, addr=zero))
    assert not unfiltered.loc_rib_filtered


def test_f_flag_is_false_for_other_peer_types():
    assert not decode_per_peer(per_peer(peer_type=0, flags=0x80, addr=bytes(16))).loc_rib_filtered


def test_per_peer_types_1_and_2_keep_the_distinguisher():
    rd = bytes.fromhex("0001fde800000064")
    assert decode_per_peer(per_peer(peer_type=1, dist=rd)).distinguisher == rd
    assert decode_per_peer(per_peer(peer_type=2, dist=rd)).peer_type == PeerType.LOCAL_INSTANCE


def test_per_peer_unknown_type_is_kept_raw():
    assert decode_per_peer(per_peer(peer_type=9)).peer_type == 9


def test_per_peer_16bit_as_padded():
    header = decode_per_peer(per_peer(asn=65000))
    assert header.asn == 65000
    assert decode_per_peer(per_peer(asn=4_200_000_000)).asn == 4_200_000_000


def test_per_peer_timestamp_zero_is_unavailable_not_epoch():
    header = decode_per_peer(per_peer(sec=0, usec=0))
    assert header.timestamp == (0, 0)
    assert not header.timestamp_available
    assert header.time is None


def test_per_peer_timestamp_is_seconds_and_microseconds_utc():
    header = decode_per_peer(per_peer(sec=1_700_000_000, usec=250_000))
    assert header.time == datetime.datetime(2023, 11, 14, 22, 13, 20, 250000, tzinfo=datetime.UTC)


@pytest.mark.parametrize("size", [0, 1, 41])
def test_per_peer_short_input_rejected(size):
    with pytest.raises(BmpError, match="needs 42 octets"):
        decode_per_peer(per_peer()[:size])


def test_per_peer_header_is_42_octets_and_extra_input_is_not_consumed():
    assert len(per_peer()) == 42
    assert decode_per_peer(per_peer() + b"\xff" * 100) == decode_per_peer(per_peer())


def test_per_peer_accepts_memoryview_and_bytearray():
    raw = per_peer(flags=0x80, addr=ipaddress.IPv6Address("::1").packed)
    assert decode_per_peer(memoryview(raw)) == decode_per_peer(bytearray(raw))
