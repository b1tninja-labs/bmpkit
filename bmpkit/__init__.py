"""bmpkit -- stop screen scraping your routers.

BMP exists precisely because obtaining route views used to mean scraping a terminal, and
Python still cannot consume it.
"""

from __future__ import annotations

from . import apps, cli, header, messages, mirror, replay, rib, server, store
from .header import BmpError, decode_common, decode_per_peer, frame
from .messages import (
    add_path_families,
    decode_bgp_pdu,
    decode_initiation,
    decode_peer_down,
    decode_peer_up,
    decode_route_mirroring,
    decode_route_monitoring,
    decode_statistics,
    decode_termination,
)
from .mirror import decode_mirrored, extract_bgp_message
from .replay import from_capture
from .rib import view_of
from .server import serve

__version__ = "0.1.0"

__all__ = [
    "BmpError",
    "__version__",
    "add_path_families",
    "apps",
    "cli",
    "decode_bgp_pdu",
    "decode_common",
    "decode_initiation",
    "decode_mirrored",
    "decode_peer_down",
    "decode_peer_up",
    "decode_per_peer",
    "decode_route_mirroring",
    "decode_route_monitoring",
    "decode_statistics",
    "decode_termination",
    "extract_bgp_message",
    "frame",
    "from_capture",
    "header",
    "messages",
    "mirror",
    "replay",
    "rib",
    "serve",
    "server",
    "store",
    "view_of",
]
