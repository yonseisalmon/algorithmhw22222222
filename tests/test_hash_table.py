import unittest

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable


class _HashTableContractTests:
    table_class = HashTable

    def test_empty_table_returns_no_value_and_does_not_remove(self):
        table = self.table_class()

        self.assertEqual(len(table), 0)
        self.assertIsNone(table.get("missing"))
        self.assertFalse(table.remove("missing"))

    def test_colliding_keys_can_be_stored_and_found(self):
        table = self.table_class()
        table.set("a", "first")
        table.set("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(len(table), 2)

    def test_setting_existing_key_updates_without_increasing_size(self):
        table = self.table_class()
        table.set("key", "old")
        table.set("key", "new")

        self.assertEqual(table.get("key"), "new")
        self.assertEqual(len(table), 1)

    def test_remove_deletes_key_and_preserves_other_colliding_keys(self):
        table = self.table_class()
        table.set("a", "first")
        table.set("i", "second")

        self.assertTrue(table.remove("a"))
        self.assertIsNone(table.get("a"))
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(len(table), 1)
        self.assertFalse(table.remove("a"))

    def test_resize_rehashes_entries_and_preserves_values(self):
        table = self.table_class(capacity=2, max_load=0.75)
        table.set("a", "first")
        table.set("i", "second")

        self.assertGreater(table.capacity, 2)
        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(len(table), 2)

    def test_non_positive_initial_capacity_is_rejected(self):
        for capacity in (0, -1):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    self.table_class(capacity)

    def test_non_string_keys_and_values_are_rejected(self):
        table = self.table_class()

        with self.assertRaises(TypeError):
            table.set(1, "value")
        with self.assertRaises(TypeError):
            table.set("key", 1)
        with self.assertRaises(TypeError):
            table.get(1)
        with self.assertRaises(TypeError):
            table.remove(1)


class HashTableTests(_HashTableContractTests, unittest.TestCase):
    table_class = HashTable

    def test_lookup_counts_nodes_in_a_collision_chain(self):
        table = HashTable()
        table.set("a", "first")
        table.set("i", "second")

        self.assertEqual(table.lookup("i"), ("second", 2))
        self.assertEqual(table.lookup("q"), (None, 2))

    def test_resize_preserves_chain_insertion_order(self):
        table = HashTable()
        keys = ["a", "i", "q", "y", "A", "I", "Q"]
        for key in keys:
            table.set(key, f"value-{key}")

        for key in keys:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), f"value-{key}")
        self.assertEqual(len(table), len(keys))
        self.assertEqual(table.lookup("Q"), ("value-Q", 4))


class LinearProbingHashTableTests(_HashTableContractTests, unittest.TestCase):
    table_class = LinearProbingHashTable

    def test_probe_wraps_from_last_slot_to_zero(self):
        table = LinearProbingHashTable(capacity=8, max_load=None)
        table.set("g", "first")
        table.set("o", "second")
        table.set("w", "third")

        self.assertEqual(table.probe_trace("w"), (7, 0, 1))
        self.assertEqual(table.lookup("w"), ("third", 3))

    def test_tombstone_preserves_probe_chain_and_can_be_reused(self):
        table = LinearProbingHashTable(capacity=8, max_load=None)
        for key in ("g", "o", "w"):
            table.set(key, key.upper())

        self.assertTrue(table.remove("o"))
        self.assertEqual(table.get("w"), "W")
        table.set("G", "replacement")

        self.assertEqual(table.get("G"), "replacement")
        self.assertEqual(table.get("w"), "W")
        self.assertEqual(table.probe_trace("G"), (7, 0))
        self.assertEqual(len(table), 3)

    def test_full_fixed_table_reports_missing_and_rejects_new_key(self):
        table = LinearProbingHashTable(capacity=2, max_load=None)
        table.set("a", "first")
        table.set("b", "second")

        self.assertEqual(table.lookup("missing"), (None, 2))
        with self.assertRaises(OverflowError):
            table.set("c", "third")

        self.assertTrue(table.remove("a"))
        table.set("c", "third")
        self.assertEqual(len(table), 2)
        self.assertEqual(table.get("c"), "third")

    def test_fixed_capacity_does_not_resize_before_it_is_full(self):
        table = LinearProbingHashTable(capacity=8, max_load=None)
        for key in ("a", "i", "q", "y", "A", "I", "Q"):
            table.set(key, key)

        self.assertEqual(table.capacity, 8)
        self.assertEqual(len(table), 7)


if __name__ == "__main__":
    unittest.main()
