import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_zero(self):
        self.assertEqual(encode(0), "0")

    def test_encode_digit_order(self):
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")

    def test_round_trip(self):
        values = [1, 9, 10, 35, 36, 61, 62, 63, 3843, 2**128]
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(decode(encode(value)), value)

    def test_decode_digit_order(self):
        self.assertEqual(decode("z"), 35)
        self.assertEqual(decode("Z"), 61)

    def test_encode_rejects_negative_integer(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_encode_rejects_non_integer(self):
        with self.assertRaises(TypeError):
            encode("1")

    def test_decode_rejects_empty_string(self):
        with self.assertRaises(ValueError):
            decode("")

    def test_decode_rejects_invalid_character(self):
        with self.assertRaises(ValueError):
            decode("a-")

    def test_decode_rejects_non_string(self):
        with self.assertRaises(TypeError):
            decode(1)


if __name__ == "__main__":
    unittest.main()
