"""passthrough of mirrored traffic for capture and replay.

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    RouteMirroring = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "extract_bgp_message",
]


def extract_bgp_message(message: RouteMirroring) -> bytes:
    """Pending behaviour defined by RFC 7854.

    Not implemented yet. See the ``mirror.extract_bgp_message()`` row in ROADMAP.md; this
    stub raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("extract_bgp_message() is not implemented: RFC 7854")
