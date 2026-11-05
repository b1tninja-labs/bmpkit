"""deterministic re-reading of a capture for tests and analysts.

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "from_capture",
]


def from_capture(path: pathlib.Path) -> Iterator:
    """Pending behaviour defined by design.

    Not implemented yet. See the ``replay.from_capture()`` row in ROADMAP.md; this stub
    raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("from_capture() is not implemented: design")
