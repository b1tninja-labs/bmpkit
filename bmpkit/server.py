"""the asyncio collector with per connection state.

``serve`` is still a placeholder until the milestone named in ROADMAP.md lands. A stub raises
instead of returning a plausible empty value: a protocol library that silently answers nothing
is worse than one that refuses to answer.

The per-connection rules that need no socket are here and are pure: :class:`Connection` frames
the byte stream under :class:`Limits` and keeps the session lifecycle of RFC 7854 section 3.3,
and :class:`Admission` is the per-address concurrency and rate policy a listener applies before
it creates a :class:`Connection`. Those limits are this library's policy: RFC 7854 section 3.2
states the shape of them for the router that accepts connections ("SHOULD restrict the number of
simultaneous connections ... from a given IP address", default 1, and "MUST also restrict the
rate", suggested 2 per minute), and the collector applies the same shape to its own listener.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .header import (
    COMMON_HEADER_LENGTH,
    MAX_MESSAGE_LENGTH,
    PER_PEER_HEADER_LENGTH,
    BmpError,
    CommonHeader,
    MsgType,
    decode_common,
)

if TYPE_CHECKING:
    from typing import Any

    Sink = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "Admission",
    "Connection",
    "LimitError",
    "Limits",
    "serve",
]

_PEER_SCOPED = (MsgType.ROUTE_MONITORING, MsgType.STATISTICS_REPORT, MsgType.ROUTE_MIRRORING)


class LimitError(BmpError):
    """A connection broke a limit or the session lifecycle. ``limit`` names which one."""

    def __init__(self, limit: str, message: str) -> None:
        super().__init__(message)
        self.limit = limit


@dataclass(frozen=True, slots=True)
class Limits:
    """The bounds one connection and one listener work within (library policy, see the module
    docstring). ``max_message_length`` caps the length field of a common header, ``max_peers`` the
    number of peers a connection holds Peer Up for at once, ``max_per_address`` the simultaneous
    connections from one address, and ``max_connections`` per ``rate_window`` seconds the
    connection rate from one address."""

    max_message_length: int = MAX_MESSAGE_LENGTH
    max_peers: int = 4096
    max_per_address: int = 1
    max_connections: int = 2
    rate_window: float = 60.0


@dataclass(slots=True)
class Connection:
    """One BMP session as seen by the monitoring station, with no socket (RFC 7854 section 3.3).

    :meth:`feed` takes the bytes read from the connection and returns the complete messages they
    finish, as ``(CommonHeader, body)``. Unrecognised message types are returned, not raised
    (section 4.1: an implementation MUST ignore them) but only after Initiation. The router "MUST
    begin by sending an Initiation message" (section 3.3), so a first message of any other type
    raises :class:`LimitError` with ``limit="initiation-first"``. A length field over
    ``max_message_length`` raises it with ``limit="message-length"`` before any body is
    buffered, and a Peer Up that would make more than ``max_peers`` peers raises
    ``limit="peers"``. After a Termination message (type 5) or any error the connection is closed
    and further bytes raise ``limit="closed"``; the caller drops the TCP session.
    """

    limits: Limits = field(default_factory=Limits)
    initiated: bool = False
    closed: bool = False
    peers: set[bytes] = field(default_factory=set)
    _buffer: bytearray = field(default_factory=bytearray)

    def feed(self, data: bytes) -> list[tuple[CommonHeader, bytes]]:
        if self.closed:
            raise LimitError("closed", "the connection is closed")
        self._buffer += data
        found: list[tuple[CommonHeader, bytes]] = []
        try:
            while len(self._buffer) >= COMMON_HEADER_LENGTH:
                try:
                    header = decode_common(self._buffer, max_length=self.limits.max_message_length)
                except BmpError as error:
                    if "exceeds the limit" in str(error):
                        raise LimitError("message-length", str(error)) from error
                    raise
                if len(self._buffer) < header.length:
                    break
                body = bytes(self._buffer[COMMON_HEADER_LENGTH : header.length])
                del self._buffer[: header.length]
                self._track(header, body)
                found.append((header, body))
                if self.closed:
                    break
        except BmpError:
            self.closed = True
            raise
        return found

    def _track(self, header: CommonHeader, body: bytes) -> None:
        kind = header.known_type
        if not self.initiated:
            if kind is not MsgType.INITIATION:
                raise LimitError("initiation-first", "the first message is not an Initiation")
            self.initiated = True
        if kind is MsgType.TERMINATION:
            self.closed = True
        elif kind in (MsgType.PEER_UP, MsgType.PEER_DOWN):
            if len(body) < PER_PEER_HEADER_LENGTH:
                raise BmpError("Peer Up or Peer Down shorter than a per-peer header")
            # identity: peer type, distinguisher and address; flags, AS, BGP ID and time vary
            key = body[0:1] + body[2:26]
            if kind is MsgType.PEER_DOWN:
                self.peers.discard(key)
            elif key not in self.peers:
                if len(self.peers) >= self.limits.max_peers:
                    raise LimitError("peers", f"more than {self.limits.max_peers} peers")
                self.peers.add(key)


@dataclass(slots=True)
class Admission:
    """Per-address admission for a listener, a pure function of the clock the caller reads.

    :meth:`admit` returns True and records the connection, or False when that address already
    holds ``max_per_address`` connections or has made ``max_connections`` in the last
    ``rate_window`` seconds (a refused attempt does not count). :meth:`release` ends one.
    """

    limits: Limits = field(default_factory=Limits)
    _open: dict[str, int] = field(default_factory=dict)
    _recent: dict[str, collections.deque[float]] = field(default_factory=dict)

    def admit(self, address: str, now: float) -> bool:
        recent = self._recent.setdefault(address, collections.deque())
        while recent and now - recent[0] >= self.limits.rate_window:
            recent.popleft()
        if self._open.get(address, 0) >= self.limits.max_per_address:
            return False
        if len(recent) >= self.limits.max_connections:
            return False
        recent.append(now)
        self._open[address] = self._open.get(address, 0) + 1
        return True

    def release(self, address: str) -> None:
        count = self._open.get(address, 0)
        if count <= 1:
            self._open.pop(address, None)
        else:
            self._open[address] = count - 1


async def serve(host: str, port: int, sink: Sink) -> None:
    """Pending behaviour defined by RFC 7854.

    Not implemented yet. See the ``server.serve()`` row in ROADMAP.md; this stub raises
    on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("serve() is not implemented: RFC 7854")
