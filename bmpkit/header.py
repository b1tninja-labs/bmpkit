"""common and per peer headers with the version and flag discipline (RFC 7854).

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    CommonHeader = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "decode_common",
]


def decode_common(raw: bytes) -> CommonHeader:
    """Pending behaviour defined by RFC 7854.

    Not implemented yet. See the ``header.decode_common()`` row in ROADMAP.md; this stub
    raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("decode_common() is not implemented: RFC 7854")
