"""bmpkit -- stop screen scraping your routers.

BMP exists precisely because obtaining route views used to mean scraping a terminal, and
Python still cannot consume it.
"""

from __future__ import annotations

from . import apps, cli, header, messages, mirror, replay, rib, server, store
from .header import decode_common
from .messages import decode_route_monitoring, decode_statistics
from .mirror import extract_bgp_message
from .replay import from_capture
from .rib import view_of
from .server import serve

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "apps",
    "cli",
    "decode_common",
    "decode_route_monitoring",
    "decode_statistics",
    "extract_bgp_message",
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
