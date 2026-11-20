"""A string-to-string hash table using linear probing and Horner hashing."""

import math
from dataclasses import dataclass

from src.hash_table import _horner_hash, _horner_hash_trace


@dataclass(slots=True)
class _Entry:
    key: str
    value: str


class _Tombstone:
    __slots__ = ()


_TOMBSTONE = _Tombstone()


class LinearProbingHashTable:
    """Open-addressed hash table with tombstones and automatic growth."""

    strategy = "linear_probing"

    def __init__(self, capacity: int = 8, max_load: float | None = 0.75) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if max_load is not None:
            if isinstance(max_load, bool) or not isinstance(max_load, (int, float)):
                raise TypeError("max_load must be a positive number or None")
            if not math.isfinite(max_load) or max_load <= 0:
                raise ValueError("max_load must be positive and finite")

        self._capacity = capacity
        self._max_load = max_load
        self._slots: list[_Entry | _Tombstone | None] = [None] * capacity
        self._size = 0

    @property
    def capacity(self) -> int:
        """Return the number of slots."""
        return self._capacity

    def __len__(self) -> int:
        return self._size

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    def _hash_index(self, key: str) -> int:
        return _horner_hash(key, self._capacity)

    def hash_trace(self, key: str) -> tuple[tuple[int, ...], int]:
        """Return Horner residues for each character and the initial slot."""
        self._validate_key(key)
        return _horner_hash_trace(key, self._capacity)

    def probe_trace(self, key: str) -> tuple[int, ...]:
        """Return slots inspected until the key or an empty slot is reached."""
        self._validate_key(key)
        start = self._hash_index(key)
        inspected = []
        for offset in range(self._capacity):
            index = (start + offset) % self._capacity
            inspected.append(index)
            slot = self._slots[index]
            if slot is None:
                break
            if isinstance(slot, _Entry) and slot.key == key:
                break
        return tuple(inspected)

    def _find(self, key: str) -> tuple[int | None, int]:
        start = self._hash_index(key)
        for probes in range(1, self._capacity + 1):
            index = (start + probes - 1) % self._capacity
            slot = self._slots[index]
            if slot is None:
                return None, probes
            if isinstance(slot, _Entry) and slot.key == key:
                return index, probes
        return None, self._capacity

    def lookup(self, key: str) -> tuple[str | None, int]:
        """Return a value (or None) and the number of slots inspected."""
        self._validate_key(key)
        index, probes = self._find(key)
        if index is None:
            return None, probes
        slot = self._slots[index]
        if not isinstance(slot, _Entry):
            raise RuntimeError("located hash-table slot is not occupied")
        return slot.value, probes

    def get(self, key: str) -> str | None:
        """Return the value for key, or None when key is absent."""
        value, _ = self.lookup(key)
        return value

    def set(self, key: str, value: str) -> None:
        """Insert or replace a string value without duplicating a key."""
        self._validate_key(key)
        if not isinstance(value, str):
            raise TypeError("value must be a string")

        start = self._hash_index(key)
        first_tombstone = None
        for offset in range(self._capacity):
            index = (start + offset) % self._capacity
            slot = self._slots[index]
            if slot is None:
                target = first_tombstone if first_tombstone is not None else index
                self._slots[target] = _Entry(key, value)
                self._size += 1
                self._grow_if_needed()
                return
            if isinstance(slot, _Tombstone):
                if first_tombstone is None:
                    first_tombstone = index
            elif slot.key == key:
                slot.value = value
                return

        if first_tombstone is not None:
            self._slots[first_tombstone] = _Entry(key, value)
            self._size += 1
            self._grow_if_needed()
            return
        if self._max_load is None:
            raise OverflowError("linear probing table is full")
        self._resize(self._capacity * 2)
        self.set(key, value)

    def remove(self, key: str) -> bool:
        """Remove key if present and report whether it was found."""
        self._validate_key(key)
        index, _ = self._find(key)
        if index is None:
            return False
        self._slots[index] = _TOMBSTONE
        self._size -= 1
        return True

    def inspect(self) -> tuple[tuple[tuple[str, str], ...], ...]:
        """Return an immutable snapshot with one row per slot."""
        slots = []
        for slot in self._slots:
            if isinstance(slot, _Entry):
                slots.append(((slot.key, slot.value),))
            else:
                slots.append(())
        return tuple(slots)

    def _grow_if_needed(self) -> None:
        while (
            self._max_load is not None
            and self._size / self._capacity > self._max_load
        ):
            self._resize(self._capacity * 2)

    def _resize(self, capacity: int) -> None:
        entries = [
            (slot.key, slot.value)
            for slot in self._slots
            if isinstance(slot, _Entry)
        ]
        self._capacity = capacity
        self._slots = [None] * capacity
        self._size = 0
        for key, value in entries:
            start = self._hash_index(key)
            for offset in range(self._capacity):
                index = (start + offset) % self._capacity
                if self._slots[index] is None:
                    self._slots[index] = _Entry(key, value)
                    self._size += 1
                    break
