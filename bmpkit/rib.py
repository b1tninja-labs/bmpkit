"""view selection across Adj-RIB-In, Adj-RIB-Out and Loc-RIB (RFC 8671, RFC 9069).

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    PeerKey = Any  # placeholder: give it a real type in the milestone that needs it
    View = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "view_of",
]


def view_of(peer: PeerKey, flags: int) -> View:
    """Pending behaviour defined by RFC 8671, RFC 9069.

    Not implemented yet. See the ``rib.view_of()`` row in ROADMAP.md; this stub raises on
    purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("view_of() is not implemented: RFC 8671, RFC 9069")
