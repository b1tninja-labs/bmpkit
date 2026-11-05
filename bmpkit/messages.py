"""route monitoring, statistics, peer down and up, initiation and termination, route
mirroring (RFC 7854).

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    PeerKey = Any  # placeholder: give it a real type in the milestone that needs it
    Stats = Any  # placeholder: give it a real type in the milestone that needs it
    Update = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "decode_route_monitoring",
    "decode_statistics",
]


def decode_route_monitoring(raw: bytes, peer: PeerKey) -> Update:
    """Pending behaviour defined by RFC 7854.

    Not implemented yet. See the ``messages.decode_route_monitoring()`` row in
    ROADMAP.md; this stub raises on purpose so nothing downstream mistakes it for working
    code.
    """
    raise NotImplementedError("decode_route_monitoring() is not implemented: RFC 7854")


def decode_statistics(raw: bytes) -> Stats:
    """Pending behaviour defined by RFC 7854.

    Not implemented yet. See the ``messages.decode_statistics()`` row in ROADMAP.md; this
    stub raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("decode_statistics() is not implemented: RFC 7854")
