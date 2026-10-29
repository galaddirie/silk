"""Deterministic contracts for silk.scraping.await_change with fake operations."""

from __future__ import annotations

import pytest
from fp_ops import operation

from silk.errors import ChangeTimeoutError
from silk.scraping import await_change


class Board:
    def __init__(self, reveal_after_reads: int | None) -> None:
        self.value = 0
        self.reads = 0
        self.actions = 0
        self.reveal_after_reads = reveal_after_reads

    def act(self, state: object) -> object:
        self.actions += 1
        return state

    def probe(self, _state: object) -> int:
        self.reads += 1
        if (
            self.reveal_after_reads is not None
            and self.reads >= self.reveal_after_reads
        ):
            self.value = 1
        return self.value


@pytest.mark.asyncio
async def test_change_ends_the_wait() -> None:
    board = Board(reveal_after_reads=4)
    waited = await_change(
        operation(board.act),
        probe=operation(board.probe),
        timeout_ms=100,
        interval_ms=1,
    )
    assert (await waited.run("page")).ok == "page"
    assert board.actions == 1


@pytest.mark.asyncio
async def test_change_seen_before_retry_is_not_acted_on_again() -> None:
    # before=1 read; attempt 1 = check + 2 polls (timeout 2 ms / 1 ms) = 3 reads;
    # the 5th read (attempt 2's re-check) sees the change: no second action.
    board = Board(reveal_after_reads=5)
    waited = await_change(
        operation(board.act),
        probe=operation(board.probe),
        timeout_ms=2,
        interval_ms=1,
        attempts=3,
    )
    assert (await waited.run("page")).is_ok()
    assert board.actions == 1


@pytest.mark.asyncio
async def test_no_change_after_every_attempt_is_a_timeout() -> None:
    board = Board(reveal_after_reads=None)
    waited = await_change(
        operation(board.act),
        probe=operation(board.probe),
        timeout_ms=2,
        interval_ms=1,
        attempts=2,
    )
    assert isinstance((await waited.run("page")).error, ChangeTimeoutError)
    assert board.actions == 2


def test_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="await_change"):
        await_change(operation(lambda s: s), probe=operation(lambda s: 1), attempts=0)
