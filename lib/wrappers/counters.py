from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, DefaultDict

from lib.factories import event_defaultdict


@dataclass
class Counter:
    _num: int = 0
    _total_increments: int = 0
    _num_waiters: DefaultDict[int, asyncio.Event] = field(default_factory=event_defaultdict, init=False)
    _total_increment_waiters: DefaultDict[int, asyncio.Event] = field(default_factory=event_defaultdict, init=False)
    max: int = None
    max_increments: int = None

    def __next__(self):
        self.increment()
        return self._num

    def increment(self) -> None:
        if self.max and self._num == self.max:
            raise ValueError(f'counter incrementing above the maximum value: {self.max}')
        if self.max_increments and self.max_increments == self._total_increments:
            raise ValueError(f'counter incremented more times than allowed: {self._total_increments}')
        self._num += 1
        self._total_increments += 1
        self._check_num_waiters()
        self._check_total_increment_waiters()

    def decrement(self) -> None:
        if self._num <= 0:
            raise ValueError('counter decremented too many times')
        self._num -= 1
        self._check_num_waiters()

    @property
    def num(self):
        return self._num

    @property
    def total_increments(self):
        return self._total_increments

    def _check_num_waiters(self):
        if self._num in self._num_waiters:
            self._num_waiters[self._num].set()
            self._num_waiters.pop(self._num)

    def _check_total_increment_waiters(self):
        if self._total_increments in self._total_increment_waiters:
            self._total_increment_waiters[self._total_increments].set()
            self._total_increment_waiters.pop(self._total_increments)

    @staticmethod
    async def _wait_for(num: int, target_num: int, waiters: DefaultDict[int, asyncio.Event]):
        if num == target_num:
            return
        event = waiters[num]
        await event.wait()

    async def wait_for(self, num: int) -> None:
        await self._wait_for(num, self._num, self._num_waiters)

    async def wait_for_total_increments(self, num: int) -> None:
        await self._wait_for(num, self._total_increments, self._total_increment_waiters)


class Counters(DefaultDict[Any, Counter]):
    default_factory = Counter

    def __missing__(self, key):
        result = self[key] = self.default_factory()
        return result

    def increment(self, key: Any) -> None:
        self[key].increment()
        pass

    def decrement(self, key: Any) -> None:
        self[key].decrement()

    async def wait_for(self, key: Any, num: int):
        counter = self[key]
        await counter.wait_for(num)

    async def wait_for_total_increments(self, key: Any, num: int) -> None:
        counter = self[key]
        await counter.wait_for_total_increments(num)

    def total_increments(self, key: Any) -> int:
        return self[key].total_increments

    def get_num(self, key: Any) -> int:
        return self[key].num

