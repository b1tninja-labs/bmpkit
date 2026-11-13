"""View selection (ROADMAP row ``rib.view_of()``): RFC 8671 section 4 and RFC 9069 section 4.

The RFCs carry no byte examples, so the flag values are built by hand from the figures: V is
0x80, L 0x40, A 0x20, O 0x10 (RFC 8671 section 4), and for peer type 3 only F at 0x80 exists
(RFC 9069 section 4.2).
"""

from __future__ import annotations

import itertools
import struct

import pytest

from bmpkit.header import decode_per_peer
from bmpkit.rib import View, loc_rib_filtered, view_of


def test_o_and_l_flags_select_the_view_for_peer_types_0_to_2():
    for peer_type in (0, 1, 2):
        assert view_of(peer_type, 0x00) is View.ADJ_RIB_IN_PRE
        assert view_of(peer_type, 0x40) is View.ADJ_RIB_IN_POST
        assert view_of(peer_type, 0x10) is View.ADJ_RIB_OUT_PRE
        assert view_of(peer_type, 0x50) is View.ADJ_RIB_OUT_POST


def test_v_and_a_and_reserved_bits_do_not_change_the_view():
    # V (0x80) and A (0x20) and the four reserved bits are not view bits (RFC 8671 section 4)
    for extra in (0x80, 0x20, 0x0F, 0xAF):
        assert view_of(0, extra) is View.ADJ_RIB_IN_PRE
        assert view_of(0, extra | 0x50) is View.ADJ_RIB_OUT_POST


def test_loc_rib_ignores_every_flag_and_f_is_the_only_one_that_means_something():
    for flags in range(256):
        assert view_of(3, flags) is View.LOC_RIB  # 0x40 and 0x10 are reserved there
        assert loc_rib_filtered(3, flags) is bool(flags & 0x80)
    assert not loc_rib_filtered(0, 0x80)  # the V flag at the same bit


def test_out_of_range_values_are_refused():
    for peer_type, flags in ((256, 0), (0, 256), (-1, 0), (0, -1)):
        with pytest.raises(ValueError, match="one octet"):
            view_of(peer_type, flags)


def test_it_agrees_with_the_header_property_and_with_bgpfeed_for_every_flag():
    events = pytest.importorskip("bmpkit.events", reason="bgpfeed is a sibling checkout")
    for peer_type, flags in itertools.product((0, 1, 2, 3), range(256)):
        raw = struct.pack(
            ">BB8s16sI4sII", peer_type, flags, bytes(8), bytes(16), 65001, bytes(4), 0, 0
        )
        header = decode_per_peer(raw, strict=False)
        assert events.view_of_header(header).value == view_of(peer_type, flags).value
        assert header.loc_rib_filtered is loc_rib_filtered(peer_type, flags)
