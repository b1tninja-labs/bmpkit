"""Information TLVs, Initiation, Termination and Peer Up bodies.

Vectors are hand-built from RFC 7854 sections 4.3, 4.4, 4.5 and 4.10 and RFC 9736 section 3
(read through rfclib on 2026-11-13); the RFCs carry no byte examples.
"""

from __future__ import annotations

import ipaddress
import struct

import pytest

from bmpkit.header import BmpError, PerPeerHeader
from bmpkit.messages import (
    InfoTlv,
    TermReason,
    decode_initiation,
    decode_peer_up,
    decode_termination,
    decode_tlvs,
)


def tlv(kind: int, value: bytes) -> bytes:
    return struct.pack(">HH", kind, len(value)) + value


def peer(peer_type: int = 0, flags: int = 0) -> PerPeerHeader:
    return PerPeerHeader(
        peer_type, flags, bytes(8), None, 65001, ipaddress.IPv4Address("10.0.0.1"), (0, 0)
    )


def bgp_open(length: int = 29, kind: int = 1) -> bytes:
    return b"\xff" * 16 + struct.pack(">HB", length, kind) + bytes(length - 19)


DESCR = tlv(1, b"Example OS 1.2")
NAME = tlv(2, b"router1")


def test_initiation_with_sysdescr_sysname():
    msg = decode_initiation(DESCR + NAME)
    assert msg.sys_descr == ("Example OS 1.2",)
    assert msg.sys_name == ("router1",)
    assert msg.strings == ()
    assert msg.missing == ()
    assert msg.tlvs == (InfoTlv(1, b"Example OS 1.2"), InfoTlv(2, b"router1"))


@pytest.mark.parametrize(
    ("body", "names"),
    [(DESCR, "sysName"), (NAME, "sysDescr"), (b"", "sysDescr, sysName")],
)
def test_initiation_missing_required_tlv_rejected_strict_reported_lenient(body, names):
    with pytest.raises(BmpError, match=names):
        decode_initiation(body)
    assert ", ".join(decode_initiation(body, strict=False).missing) == names


def test_initiation_multiple_string_tlvs_preserved_in_order():
    body = tlv(0, b"first") + DESCR + tlv(0, b"second") + NAME + tlv(0, b"third")
    assert decode_initiation(body).strings == ("first", "second", "third")


def test_initiation_unknown_tlv_kept_in_other():
    body = DESCR + NAME + tlv(999, b"\x01\x02")
    assert decode_initiation(body).other == (InfoTlv(999, b"\x01\x02"),)


def test_initiation_rfc9736_peer_up_types_are_reserved_not_strings():
    # RFC 9736 table 3: types 3 and 4 are Reserved in the Initiation registry.
    msg = decode_initiation(DESCR + NAME + tlv(3, b"vrf") + tlv(4, b"label"))
    assert msg.other == (InfoTlv(3, b"vrf"), InfoTlv(4, b"label"))
    assert msg.strings == ()


def test_initiation_repeated_sysname_all_kept():
    assert decode_initiation(DESCR + NAME + tlv(2, b"again")).sys_name == ("router1", "again")


def test_tlv_length_overruns_body():
    with pytest.raises(BmpError, match="remain"):
        decode_tlvs(struct.pack(">HH", 1, 10) + b"short")


@pytest.mark.parametrize("raw", [b"\x00", b"\x00\x01\x00", DESCR + b"\x00\x00\x00"])
def test_tlv_truncated_header(raw):
    with pytest.raises(BmpError, match="TLV header"):
        decode_tlvs(raw)


def test_tlv_zero_length_string():
    msg = decode_initiation(DESCR + NAME + tlv(0, b""))
    assert msg.strings == ("",)


def test_string_invalid_utf8_strict_refused_lenient_keeps_octets():
    body = DESCR + NAME + tlv(0, b"caf\xe9")
    with pytest.raises(BmpError, match="UTF-8"):
        decode_initiation(body)
    kept = decode_initiation(body, strict=False).strings[0]
    assert kept.encode("utf-8", errors="surrogateescape") == b"caf\xe9"


def test_string_valid_utf8_beyond_ascii():
    assert decode_initiation(DESCR + NAME + tlv(0, "café".encode())).strings == ("café",)


def test_too_many_tlvs_refused():
    body = tlv(0, b"") * 5
    with pytest.raises(BmpError, match="more than 4 TLVs"):
        decode_tlvs(body, max_tlvs=4)
    assert len(decode_tlvs(body, max_tlvs=5)) == 5


def test_trailing_garbage_after_last_tlv_rejected():
    with pytest.raises(BmpError, match="trailing"):
        decode_initiation(DESCR + NAME + b"\x01\x02")


def test_decode_tlvs_accepts_memoryview_and_bytearray():
    raw = DESCR + NAME
    assert decode_tlvs(memoryview(raw)) == decode_tlvs(bytearray(raw)) == decode_tlvs(raw)


@pytest.mark.parametrize("code", range(5))
def test_termination_each_reason_code_0_to_4(code):
    msg = decode_termination(tlv(1, struct.pack(">H", code)))
    assert msg.reason == code
    assert msg.known_reason == TermReason(code)


def test_termination_reason_required():
    with pytest.raises(BmpError, match="REQUIRED Reason"):
        decode_termination(tlv(0, b"bye"))
    lenient = decode_termination(tlv(0, b"bye"), strict=False)
    assert lenient.reason is None
    assert lenient.known_reason is None
    assert lenient.strings == ("bye",)


def test_termination_unknown_reason_code_kept_raw():
    msg = decode_termination(tlv(1, struct.pack(">H", 4242)))
    assert msg.reason == 4242
    assert msg.known_reason is None


@pytest.mark.parametrize("value", [b"", b"\x00", b"\x00\x00\x00"])
def test_reason_tlv_wrong_length_rejected(value):
    with pytest.raises(BmpError, match="not 2"):
        decode_termination(tlv(1, value))
    with pytest.raises(BmpError, match="not 2"):
        decode_termination(tlv(1, value), strict=False)


def test_termination_repeated_reason_refused_strict():
    body = tlv(1, b"\x00\x00") + tlv(1, b"\x00\x01")
    with pytest.raises(BmpError, match="more than one"):
        decode_termination(body)


def test_termination_strings_in_order_and_unknown_tlv_kept():
    body = tlv(0, b"a") + tlv(1, b"\x00\x02") + tlv(0, b"b") + tlv(77, b"z")
    msg = decode_termination(body)
    assert msg.strings == ("a", "b")
    assert msg.other == (InfoTlv(77, b"z"),)
    assert msg.reason == TermReason.OUT_OF_RESOURCES


def test_termination_trailing_garbage_rejected():
    with pytest.raises(BmpError, match="trailing"):
        decode_termination(tlv(1, b"\x00\x00") + b"\x00")


def peer_up_body(local: bytes, tlvs: bytes = b"", sent: bytes | None = None) -> bytes:
    return (
        local
        + struct.pack(">HH", 179, 40000)
        + (sent if sent is not None else bgp_open())
        + bgp_open(33)
        + tlvs
    )


def test_peer_up_ipv4_with_rfc9736_tlvs():
    local = bytes(12) + bytes([192, 0, 2, 2])
    body = peer_up_body(local, tlv(3, b"vrf-red") + tlv(4, b"edge") + tlv(0, b"hello"))
    msg = decode_peer_up(body, peer())
    assert msg.local_address == ipaddress.IPv4Address("192.0.2.2")
    assert (msg.local_port, msg.remote_port) == (179, 40000)
    assert msg.sent_open == bgp_open()
    assert msg.received_open == bgp_open(33)
    assert msg.vrf_names == ("vrf-red",)
    assert msg.admin_labels == ("edge",)
    assert msg.strings == ("hello",)


def test_peer_up_ipv6_local_address_from_v_flag():
    local = ipaddress.IPv6Address("2001:db8::2").packed
    msg = decode_peer_up(peer_up_body(local), peer(flags=0x80))
    assert msg.local_address == ipaddress.IPv6Address("2001:db8::2")


def test_peer_up_without_information_is_valid():
    assert decode_peer_up(peer_up_body(bytes(16)), peer()).tlvs == ()


def test_peer_up_rfc9736_reserved_types_1_and_2_are_kept_not_interpreted():
    # RFC 9736 table 2: types 1 and 2 are Reserved in the Peer Up registry (they were sysDescr/sysName).
    msg = decode_peer_up(peer_up_body(bytes(16), tlv(1, b"descr") + tlv(2, b"name")), peer())
    assert msg.other == (InfoTlv(1, b"descr"), InfoTlv(2, b"name"))
    assert msg.vrf_names == ()


def test_peer_up_vrf_name_length_1_to_255():
    with pytest.raises(BmpError, match="1 to 255"):
        decode_peer_up(peer_up_body(bytes(16), tlv(3, b"")), peer())
    with pytest.raises(BmpError, match="1 to 255"):
        decode_peer_up(peer_up_body(bytes(16), tlv(3, b"x" * 256)), peer())
    assert decode_peer_up(peer_up_body(bytes(16), tlv(3, b"x" * 255)), peer()).vrf_names == (
        "x" * 255,
    )


def test_peer_up_vrf_name_repeated_in_order():
    body = peer_up_body(bytes(16), tlv(3, b"one") + tlv(3, b"two"))
    assert decode_peer_up(body, peer()).vrf_names == ("one", "two")


def test_peer_up_loc_rib_has_no_local_address():
    # RFC 9069 section 5.2: the local address is zero-filled and not applicable.
    msg = decode_peer_up(peer_up_body(bytes(16)), peer(peer_type=3, flags=0x80))
    assert msg.local_address is None


def test_peer_up_ipv4_local_nonzero_fill_refused_strict():
    local = bytes([1]) + bytes(11) + bytes([192, 0, 2, 2])
    with pytest.raises(BmpError, match="zero-filled"):
        decode_peer_up(peer_up_body(local), peer())
    assert decode_peer_up(peer_up_body(local), peer(), strict=False).local_address == (
        ipaddress.IPv4Address("192.0.2.2")
    )


def test_peer_up_open_message_must_be_an_open_and_fit():
    with pytest.raises(BmpError, match="not OPEN"):
        decode_peer_up(peer_up_body(bytes(16), sent=bgp_open(29, kind=2)), peer())
    short = b"\xff" * 16 + struct.pack(">HB", 500, 1)
    with pytest.raises(BmpError, match="does not fit"):
        decode_peer_up(peer_up_body(bytes(16), sent=short), peer())
    tiny = b"\xff" * 16 + struct.pack(">HB", 5, 1)
    with pytest.raises(BmpError, match="does not fit"):
        decode_peer_up(peer_up_body(bytes(16), sent=tiny), peer())


@pytest.mark.parametrize("size", [0, 19])
def test_peer_up_short_body_rejected(size):
    with pytest.raises(BmpError, match="shorter than"):
        decode_peer_up(bytes(size), peer())


def test_peer_up_second_open_missing_rejected():
    body = bytes(16) + struct.pack(">HH", 1, 2) + bgp_open()
    with pytest.raises(BmpError, match="received OPEN"):
        decode_peer_up(body, peer())


# -- Statistics Reports (RFC 7854 section 4.8, RFC 8671 table 2, RFC 9972 sections 3 and 8) ----------------


def stat(stat_type: int, data: bytes) -> bytes:
    return struct.pack(">HH", stat_type, len(data)) + data


def report(*stats: bytes, count: int | None = None) -> bytes:
    return struct.pack(">I", len(stats) if count is None else count) + b"".join(stats)


def per_family(afi: int, safi: int, value: int) -> bytes:
    return struct.pack(">HBQ", afi, safi, value)


def test_statistics_report_reads_counters_gauges_and_per_family_gauges():
    from bmpkit.messages import decode_statistics

    body = report(
        stat(0, struct.pack(">I", 5)),
        stat(7, struct.pack(">Q", 2**40)),
        stat(9, per_family(1, 1, 700)),
        stat(9, per_family(2, 1, 12)),
        stat(14, struct.pack(">Q", 3)),
        stat(18, struct.pack(">Q", 4)),
        stat(22, per_family(1, 1, 8)),
        stat(43, per_family(2, 1, 9)),
    )
    stats = decode_statistics(body)
    assert [i.kind for i in stats.items] == [
        "counter32",
        "gauge64",
        "afi-safi-gauge64",
        "afi-safi-gauge64",
        "gauge64",
        "gauge64",
        "afi-safi-gauge64",
        "afi-safi-gauge64",
    ]
    assert stats.get(0) == 5
    assert stats.get(7) == 2**40
    assert stats.get(9, 1, 1) == 700
    assert stats.get(9, 2, 1) == 12
    assert stats.get(9, 1, 2) is None
    assert stats.get(22, 1, 1) == 8
    assert stats.get(43, 2, 1) == 9


def test_statistics_unknown_types_are_kept_and_not_interpreted():
    from bmpkit.messages import decode_statistics

    stats = decode_statistics(
        report(stat(24, b"\x01\x02"), stat(500, b""), stat(1, struct.pack(">I", 1)))
    )
    assert [(i.type, i.kind, i.value, i.raw) for i in stats.items] == [
        (24, "unknown", None, b"\x01\x02"),
        (500, "unknown", None, b""),
        (1, "counter32", 1, struct.pack(">I", 1)),
    ]


@pytest.mark.parametrize(
    ("body", "match"),
    [
        (b"\x00\x00", "Stats Count"),
        (report(), "at least one"),
        (report(stat(0, b"\x00" * 8)), "needs 4"),
        (report(stat(7, b"\x00" * 4)), "needs 8"),
        (report(stat(19, b"\x00" * 8)), "needs 11"),
        (report(stat(18, struct.pack(">Q", 1)), stat(18, struct.pack(">Q", 2))), "twice"),
        (report(stat(19, per_family(1, 1, 1)), stat(19, per_family(1, 1, 2))), "twice"),
        (report(stat(0, struct.pack(">I", 1)), count=2), "cut short"),
        (report(stat(0, struct.pack(">I", 1)), count=1) + b"\x00", "follow"),
        (struct.pack(">IHH", 1, 0, 40) + b"\x00", "past the end"),
        (struct.pack(">I", 10**6), "limit"),
    ],
)
def test_a_statistics_report_that_breaks_its_rules_is_refused(body, match):
    from bmpkit.messages import decode_statistics

    with pytest.raises(BmpError, match=match):
        decode_statistics(body)


def test_statistics_without_strict_keep_what_strict_refuses():
    from bmpkit.messages import decode_statistics

    odd = decode_statistics(report(stat(0, b"\x00" * 8)), strict=False)
    assert (odd.items[0].kind, odd.items[0].value) == ("unknown", None)
    assert decode_statistics(report(), strict=False).items == ()
    twice = report(stat(18, struct.pack(">Q", 1)), stat(18, struct.pack(">Q", 2)))
    assert len(decode_statistics(twice, strict=False).items) == 2
    # repeats are only forbidden for RFC 9972's types: RFC 7854 says nothing of them
    again = report(stat(7, struct.pack(">Q", 1)), stat(7, struct.pack(">Q", 2)))
    assert decode_statistics(again).get(7) == 1


def test_peer_down_tlvs_other_than_the_vrf_name_are_kept_raw():
    """RFC 9069 section 5.3 defines only type 3 for reason 6; nothing else is interpreted."""
    from bmpkit.messages import InfoTlv, decode_peer_down

    body = bytes([6]) + struct.pack(">HH", 3, 1) + b"v" + struct.pack(">HH", 9, 2) + b"\xde\xad"
    down = decode_peer_down(body)
    assert down.vrf_names == ("v",)
    assert down.tlvs == (InfoTlv(3, b"v"), InfoTlv(9, b"\xde\xad"))
