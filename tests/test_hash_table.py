import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_empty_table_returns_no_value_and_does_not_remove(self):
        table = HashTable()

        self.assertEqual(len(table), 0)
        self.assertIsNone(table.get("missing"))
        self.assertFalse(table.remove("missing"))
        self.assertEqual(table.lookup("missing"), (None, 0))

    def test_colliding_keys_can_be_stored_and_found(self):
        table = HashTable()
        table.set("a", "first")
        table.set("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(len(table), 2)
        self.assertEqual(table.lookup("i"), ("second", 2))
        self.assertEqual(table.lookup("q"), (None, 2))

    def test_setting_existing_key_updates_without_increasing_size(self):
        table = HashTable()
        table.set("key", "old")
        table.set("key", "new")

        self.assertEqual(table.get("key"), "new")
        self.assertEqual(len(table), 1)

    def test_remove_deletes_key_and_preserves_other_colliding_keys(self):
        table = HashTable()
        table.set("a", "first")
        table.set("i", "second")

        self.assertTrue(table.remove("a"))
        self.assertIsNone(table.get("a"))
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(len(table), 1)
        self.assertFalse(table.remove("a"))

    def test_resize_rehashes_entries_and_preserves_values(self):
        table = HashTable()
        keys = ["a", "i", "q", "y", "A", "I", "Q"]
        for key in keys:
            table.set(key, f"value-{key}")

        for key in keys:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), f"value-{key}")
        self.assertEqual(len(table), len(keys))
        # All seven keys collide at capacity 8; after growth to 16, four share Q's bucket.
        self.assertEqual(table.lookup("Q"), ("value-Q", 4))

    def test_non_positive_initial_capacity_is_rejected(self):
        for capacity in (0, -1):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    HashTable(capacity)

    def test_non_string_keys_and_values_are_rejected(self):
        table = HashTable()

        with self.assertRaises(TypeError):
            table.set(1, "value")
        with self.assertRaises(TypeError):
            table.set("key", 1)
        with self.assertRaises(TypeError):
            table.get(1)
        with self.assertRaises(TypeError):
            table.remove(1)


if __name__ == "__main__":
    unittest.main()
