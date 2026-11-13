"""passthrough of mirrored traffic for capture and replay (RFC 7854 sections 4.7 and 6).

A Route Mirroring message carries a verbatim BGP PDU in its BGP Message TLV. ``extract_bgp_message``
returns those octets untouched, which is what a capture or replay store wants; ``decode_mirrored``
hands them to ``pathattr``. A mirrored PDU may be the one that was treated as withdraw (Errored PDU,
RFC 7606), so decoding it can legitimately raise; the verbatim octets are always available.
"""

from __future__ import annotations

from typing import Any

from .header import BmpError, PerPeerHeader
from .messages import RouteMirroring, decode_bgp_pdu

__all__ = [
    "decode_mirrored",
    "extract_bgp_message",
]


def extract_bgp_message(message: RouteMirroring) -> bytes:
    """The verbatim BGP PDU of a Route Mirroring message (RFC 7854 section 4.7).

    Raises :class:`BmpError` when the message has no BGP Message TLV, as one carrying only a
    Messages Lost Information code does.
    """
    if message.bgp_message is None:
        raise BmpError("the Route Mirroring message has no BGP Message TLV")
    return message.bgp_message


def decode_mirrored(message: RouteMirroring, peer: PerPeerHeader, **options: Any) -> Any:
    """Decode the mirrored BGP PDU with ``pathattr`` (see :func:`bmpkit.messages.decode_bgp_pdu`).

    Raises :class:`BmpError` when there is no PDU or ``pathattr`` refuses it, which an Errored PDU
    may well deserve. The per-peer L flag has no meaning for mirrored messages (verified erratum
    7703 to RFC 7854 section 4.2) and is not consulted.
    """
    return decode_bgp_pdu(extract_bgp_message(message), peer, **options)
