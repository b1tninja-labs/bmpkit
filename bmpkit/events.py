"""BMP messages as ``bgpfeed.model.Event`` (PORTFOLIO section 9 item 15: bmpkit adopts bgpfeed's model).

Only ``bgpfeed.model`` is imported (bgpfeed's package namespace is lazy, so that loads neither
asnkit nor pathattr), and the decoded UPDATE comes from this package's own decoders, which use
``pathattr``. bgpfeed is a sibling project on ``pythonpath`` and ``mypy_path``; this module is
not imported by ``bmpkit/__init__`` so the rest of the package does not need it.

What each message becomes:

* Route Monitoring (RFC 7854 section 4.6) gives a WITHDRAW event per withdrawn prefix (IPv4
  Withdrawn Routes and MP_UNREACH_NLRI) and an ANNOUNCE event per announced prefix (IPv4 NLRI and
  MP_REACH_NLRI), each carrying the raw AS_PATH of the UPDATE. An UPDATE that RFC 7606 says to
  treat as a withdrawal turns its announcements into WITHDRAW events with reason
  ``"treat-as-withdraw"``; one that needs the AFI/SAFI disabled or a session reset is refused with
  :class:`~bmpkit.header.BmpError`, because its NLRI cannot be trusted. An End-of-RIB marker has no
  prefix and gives no event.
* Peer Up gives a PEER_STATE event with ``session`` UP; Peer Down one with ``session`` DOWN and a
  ``reason`` naming the Peer Down reason code (RFC 7854 section 4.9, RFC 9069 section 5.3). Neither
  message carries BGP FSM state numbers, so ``old_state`` and ``new_state`` stay ``None``.

``Event.time`` is the per-peer timestamp, ``None`` when it is zero (RFC 7854 section 4.2).
``Event.view`` (Route Monitoring only; Peer Up and Down have no RIB) is read from the per-peer header: peer type 3 is Loc-RIB (RFC 9069 section 4), and
otherwise the O flag (RFC 8671 section 4) selects Adj-RIB-Out and the L flag post-policy
(RFC 7854 section 4.2, RFC 8671 section 5). ``Peer.address`` is ``None`` for the Loc-RIB Instance
Peer. The AS_PATH width follows the A flag; Loc-RIB is always 4-octet (RFC 9069 section 5.4.1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bgpfeed.model import Event, EventKind, Network, Peer, RibView, SessionState
from pathattr.attribute import Action

from .header import BmpError, PerPeerHeader
from .messages import PeerDown, PeerDownReason, PeerUp, RouteMonitoring

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "peer_down_event",
    "peer_of",
    "peer_up_event",
    "route_monitoring_events",
    "view_of_header",
]

_AS_PATH = 2


def peer_of(header: PerPeerHeader) -> Peer:
    """The :class:`Peer` a per-peer header names, with its distinguisher and BGP ID."""
    return Peer(header.address, header.asn, header.distinguisher, header.bgp_id)


def view_of_header(header: PerPeerHeader) -> RibView:
    """The RIB view of a Route Monitoring message from its per-peer header (see the module docstring)."""
    if header.is_loc_rib:
        return RibView.LOC_RIB
    if header.adj_rib_out:
        return RibView.ADJ_RIB_OUT_POST if header.post_policy else RibView.ADJ_RIB_OUT_PRE
    return RibView.ADJ_RIB_IN_POST if header.post_policy else RibView.ADJ_RIB_IN_PRE


def route_monitoring_events(
    message: RouteMonitoring, header: PerPeerHeader, *, source: str
) -> Iterator[Event]:
    """Yield the events of a decoded Route Monitoring message (see the module docstring).

    ``message`` comes from :func:`bmpkit.messages.decode_route_monitoring` and ``header`` is the
    per-peer header it was decoded with. Raises :class:`~bmpkit.header.BmpError` for an UPDATE
    whose RFC 7606 verdict is to disable the AFI/SAFI or reset the session.
    """
    update = message.update
    if update.action >= Action.AFI_SAFI_DISABLE:
        raise BmpError(f"UPDATE needs {update.action.name}; its NLRI is not trusted")
    treat = update.action == Action.TREAT_AS_WITHDRAW
    when = header.time
    peer = peer_of(header)
    view = view_of_header(header)
    four = header.is_loc_rib or not header.legacy_as_path
    as_path = next((a.value for a in update.attributes if a.type_code == _AS_PATH), None)

    def withdraw(prefix: Network, path_id: int | None) -> Event:
        return Event(
            when, source, peer, EventKind.WITHDRAW,
            prefix=prefix, path_id=path_id, four_octet_as=four, view=view,
        )  # fmt: skip

    def announce(prefix: Network, path_id: int | None) -> Event:
        if treat:
            return Event(
                when, source, peer, EventKind.WITHDRAW,
                prefix=prefix, path_id=path_id, four_octet_as=four, view=view,
                reason="treat-as-withdraw",
            )  # fmt: skip
        return Event(
            when, source, peer, EventKind.ANNOUNCE,
            prefix=prefix, path_id=path_id, as_path=as_path, four_octet_as=four, view=view,
        )  # fmt: skip

    for index, prefix in enumerate(update.withdrawn):
        yield withdraw(
            prefix, update.withdrawn_path_ids[index] if update.withdrawn_path_ids else None
        )
    for index, prefix in enumerate(update.nlri):
        yield announce(prefix, update.nlri_path_ids[index] if update.nlri_path_ids else None)
    unreach = message.attributes.mp_unreach
    if unreach is not None and unreach.nlri is not None:
        for entry in unreach.nlri:
            yield withdraw(entry.prefix, entry.path_id)
    reach = message.attributes.mp_reach
    if reach is not None and reach.nlri is not None:
        for entry in reach.nlri:
            yield announce(entry.prefix, entry.path_id)


def peer_up_event(up: PeerUp, header: PerPeerHeader, *, source: str) -> Event:
    """The PEER_STATE event for a Peer Up message: ``session`` UP, no FSM numbers."""
    del up  # nothing in it is part of the event; the OPENs and TLVs stay on the PeerUp
    return Event(
        header.time, source, peer_of(header), EventKind.PEER_STATE,
        session=SessionState.UP,
    )  # fmt: skip


def peer_down_event(down: PeerDown, header: PerPeerHeader, *, source: str) -> Event:
    """The PEER_STATE event for a Peer Down message: ``session`` DOWN, ``reason`` the reason code.

    The reason is the lower-case name of the :class:`~bmpkit.messages.PeerDownReason` with
    hyphens (``"remote-notification"``), or ``"reason-<n>"`` for a code the registry has not
    assigned to this library.
    """
    known = down.known_reason
    reason = (
        known.name.lower().replace("_", "-")
        if isinstance(known, PeerDownReason)
        else f"reason-{down.reason}"
    )
    return Event(
        header.time, source, peer_of(header), EventKind.PEER_STATE,
        session=SessionState.DOWN, reason=reason,
    )  # fmt: skip
