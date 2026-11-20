import unittest

from src.shortener import Shortener


class ShortenerTests(unittest.TestCase):
    def setUp(self):
        self.shortener = Shortener()

    def test_first_code_is_zero_and_round_trips_http_url(self):
        url = "http://example.com"

        code = self.shortener.shorten(url)

        self.assertEqual(code, "0")
        self.assertEqual(self.shortener.expand(code), url)

    def test_https_url_is_preserved_exactly(self):
        url = "https://example.com/a?b=1&c=two"

        code = self.shortener.shorten(url)

        self.assertEqual(self.shortener.expand(code), url)

    def test_shortening_same_url_returns_existing_code(self):
        url = "https://example.com/path"

        first_code = self.shortener.shorten(url)
        second_code = self.shortener.shorten(url)

        self.assertEqual(first_code, second_code)

    def test_different_urls_receive_different_codes(self):
        first_code = self.shortener.shorten("https://example.com/one")
        second_code = self.shortener.shorten("https://example.com/two")

        self.assertNotEqual(first_code, second_code)

    def test_url_input_is_not_normalized(self):
        url = "HTTP://Example.com/a"

        code = self.shortener.shorten(url)

        self.assertEqual(self.shortener.expand(code), url)

    def test_invalid_urls_are_rejected(self):
        invalid_urls = [
            "",
            "ftp://example.com",
            "example.com/path",
            "https:///path",
            " https://example.com",
            "https://example.com/path with space",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.shortener.shorten(url)

    def test_non_string_url_is_rejected(self):
        with self.assertRaises(TypeError):
            self.shortener.shorten(123)

    def test_empty_invalid_and_noncanonical_codes_are_rejected(self):
        for code in ("", "a-", "00"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    self.shortener.expand(code)

    def test_valid_but_unknown_code_is_rejected(self):
        with self.assertRaises(KeyError):
            self.shortener.expand("Z")

    def test_non_string_code_is_rejected(self):
        with self.assertRaises(TypeError):
            self.shortener.expand(1)


if __name__ == "__main__":
    unittest.main()
