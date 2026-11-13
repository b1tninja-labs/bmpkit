"""view selection across Adj-RIB-In, Adj-RIB-Out and Loc-RIB (RFC 8671, RFC 9069).

The view of a Route Monitoring message is a function of the per-peer header's peer type and
flags, and of nothing else:

* peer type 3 is the Loc-RIB Instance Peer (RFC 9069 section 4.1). Its flags are redefined: only F
  (0x80, "the Loc-RIB is filtered") means anything, the other bits are reserved and ignored
  (RFC 9069 section 4.2), so V, L, A and O are not read there;
* for every other peer type the O flag (0x10) selects Adj-RIB-Out over Adj-RIB-In (RFC 8671
  section 4), and the L flag (0x40) selects post-policy over pre-policy (RFC 7854 section 4.2;
  RFC 8671 sections 5.1 and 5.2 say the L flag MUST be 1 for post-policy Adj-RIB-Out and 0 for
  pre-policy).

:class:`View` carries the same five values as ``bgpfeed.model.RibView`` and the same strings, and
imports nothing, so this module works without bgpfeed; ``bmpkit.events.view_of_header`` answers
the same question for a decoded header and a test pins that they agree.
"""

from __future__ import annotations

import enum

__all__ = [
    "View",
    "loc_rib_filtered",
    "view_of",
]

_LOC_RIB = 3
_L = 0x40
_O = 0x10
_F = 0x80


class View(enum.StrEnum):
    """Which RIB a Route Monitoring message reports."""

    ADJ_RIB_IN_PRE = "adj-rib-in-pre"
    ADJ_RIB_IN_POST = "adj-rib-in-post"
    ADJ_RIB_OUT_PRE = "adj-rib-out-pre"
    ADJ_RIB_OUT_POST = "adj-rib-out-post"
    LOC_RIB = "loc-rib"


def view_of(peer_type: int, flags: int) -> View:
    """The RIB view for a per-peer header's ``peer_type`` and ``flags`` (RFC 8671, RFC 9069).

    ``peer_type`` is the one-octet peer type and ``flags`` the one-octet flags field, both as
    :func:`bmpkit.header.decode_per_peer` keeps them. See the module docstring for the rules.
    Raises ``ValueError`` for either value outside 0 to 255.
    """
    if not (0 <= peer_type <= 0xFF and 0 <= flags <= 0xFF):
        raise ValueError("peer type and flags are one octet each")
    if peer_type == _LOC_RIB:
        return View.LOC_RIB
    post = bool(flags & _L)
    if flags & _O:
        return View.ADJ_RIB_OUT_POST if post else View.ADJ_RIB_OUT_PRE
    return View.ADJ_RIB_IN_POST if post else View.ADJ_RIB_IN_PRE


def loc_rib_filtered(peer_type: int, flags: int) -> bool:
    """True for a Loc-RIB Instance Peer whose F flag says a filter was applied (RFC 9069 4.2).

    False for every other peer type, where bit 0x80 is the V flag.
    """
    return peer_type == _LOC_RIB and bool(flags & _F)
