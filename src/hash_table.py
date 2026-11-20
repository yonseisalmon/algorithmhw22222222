"""A string-to-string hash table using separate chaining and Horner hashing."""

import math
from dataclasses import dataclass


@dataclass(slots=True)
class _Node:
    key: str
    value: str
    order: int
    next: "_Node | None" = None


class HashTable:
    """Hash table with insertion-ordered chains and automatic growth."""

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
        self._buckets: list[_Node | None] = [None] * capacity
        self._size = 0
        self._next_order = 0

    @property
    def capacity(self) -> int:
        """Return the number of buckets."""
        return self._capacity

    def __len__(self) -> int:
        return self._size

    def _validate_key(self, key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    def _hash_index(self, key: str) -> int:
        value = 0
        for character in key:
            value = (value * 31 + ord(character)) % self._capacity
        return value

    def hash_trace(self, key: str) -> tuple[tuple[int, ...], int]:
        """Return Horner residues for each character and the final bucket index."""
        self._validate_key(key)
        value = 0
        steps = []
        for character in key:
            value = (value * 31 + ord(character)) % self._capacity
            steps.append(value)
        return tuple(steps), value

    def _find(self, key: str) -> tuple[_Node | None, int]:
        node = self._buckets[self._hash_index(key)]
        comparisons = 0
        while node is not None:
            comparisons += 1
            if node.key == key:
                return node, comparisons
            node = node.next
        return None, comparisons

    def lookup(self, key: str) -> tuple[str | None, int]:
        """Return a value (or None) and the number of chain nodes inspected."""
        self._validate_key(key)
        node, comparisons = self._find(key)
        return (node.value if node is not None else None), comparisons

    def get(self, key: str) -> str | None:
        """Return the value for key, or None when key is absent."""
        value, _ = self.lookup(key)
        return value

    def set(self, key: str, value: str) -> None:
        """Insert or replace a string value without duplicating a key."""
        self._validate_key(key)
        if not isinstance(value, str):
            raise TypeError("value must be a string")

        node, _ = self._find(key)
        if node is not None:
            node.value = value
            return

        bucket_index = self._hash_index(key)
        new_node = _Node(key, value, self._next_order)
        self._next_order += 1
        head = self._buckets[bucket_index]
        if head is None:
            self._buckets[bucket_index] = new_node
        else:
            tail = head
            while tail.next is not None:
                tail = tail.next
            tail.next = new_node

        self._size += 1
        while (
            self._max_load is not None
            and self._size / self._capacity > self._max_load
        ):
            self._resize(self._capacity * 2)

    def remove(self, key: str) -> bool:
        """Remove key if present and report whether it was found."""
        self._validate_key(key)
        bucket_index = self._hash_index(key)
        previous = None
        node = self._buckets[bucket_index]
        while node is not None:
            if node.key == key:
                if previous is None:
                    self._buckets[bucket_index] = node.next
                else:
                    previous.next = node.next
                self._size -= 1
                return True
            previous = node
            node = node.next
        return False

    def inspect(self) -> tuple[tuple[tuple[str, str], ...], ...]:
        """Return an immutable snapshot of the bucket chains."""
        buckets = []
        for head in self._buckets:
            chain = []
            node = head
            while node is not None:
                chain.append((node.key, node.value))
                node = node.next
            buckets.append(tuple(chain))
        return tuple(buckets)

    def _resize(self, capacity: int) -> None:
        entries = []
        for head in self._buckets:
            node = head
            while node is not None:
                entries.append((node.order, node.key, node.value))
                node = node.next

        self._capacity = capacity
        self._buckets = [None] * capacity
        for order, key, value in sorted(entries):
            bucket_index = self._hash_index(key)
            new_node = _Node(key, value, order)
            head = self._buckets[bucket_index]
            if head is None:
                self._buckets[bucket_index] = new_node
            else:
                tail = head
                while tail.next is not None:
                    tail = tail.next
                tail.next = new_node
