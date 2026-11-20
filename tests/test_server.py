import http.client
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable
from src.server import DEMO_URLS, ShortenerHandler, _seed_demo_data
from src.shortener import Shortener


class ServerTests(unittest.TestCase):
    table_class = HashTable

    def setUp(self):
        shortener = Shortener(table_class=self.table_class)
        handler = partial(ShortenerHandler, shortener=shortener)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]
        self.shortener = shortener

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.headers, response.read().decode("utf-8")
        connection.close()
        return result

    def shorten(self, url):
        body = urlencode({"url": url})
        return self.request(
            "POST",
            "/shorten",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    def test_home_page_has_url_input_form(self):
        status, _, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn('name="url"', body)
        self.assertIn('action="/shorten"', body)

    def test_shortening_shows_short_link_and_code_redirects(self):
        url = "https://example.com/a?b=1"
        status, _, body = self.shorten(url)

        self.assertEqual(status, 200)
        self.assertIn('href="/0">/0</a>', body)
        self.assertNotIn(f"http://127.0.0.1:{self.port}/0", body)

        status, headers, _ = self.request("GET", "/0")
        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], url)

    def test_invalid_url_shows_bad_request(self):
        status, _, body = self.shorten("ftp://example.com")

        self.assertEqual(status, 400)
        self.assertIn("잘못된 URL", body)

    def test_table_shows_nodes_links_and_strategy_details(self):
        first_url = "https://example.com/a"
        second_url = "https://example.com/i"
        self.shorten(first_url)
        self.shorten(second_url)

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn(first_url, body)
        self.assertIn(second_url, body)
        self.assertIn('href="/0">/0</a>', body)
        self.assertIn('href="/1">/1</a>', body)
        self.assertIn("<details", body)
        self.assertIn("호너 해시", body)
        if self.shortener.table_strategy == "linear_probing":
            self.assertIn("선형 탐사 경로", body)
            self.assertIn("충돌 처리: 선형 탐지", body)
            self.assertIn("→", body)
        else:
            self.assertIn("충돌 처리: 개별 체이닝", body)
            self.assertIn("→", body)

    def test_table_escapes_url_content(self):
        url = "https://example.com/<script>"
        status, _, _ = self.shorten(url)
        self.assertEqual(status, 200)

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn("<script>", body)

    def test_demo_urls_make_collisions_visible_for_each_strategy(self):
        self.assertEqual(
            [self.shortener.hash_trace(url)[1] for url in DEMO_URLS],
            [0, 0, 0],
        )
        _seed_demo_data(self.shortener)

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        for code, url in enumerate(DEMO_URLS):
            self.assertIn(url, body)
            self.assertIn(f'href="/{code}">/{code}</a>', body)
        if self.shortener.table_strategy == "linear_probing":
            self.assertIn("해시 충돌: 시작 칸이 점유되어", body)
            self.assertIn("선형 탐사 경로: <code>0 → 1 → 2</code>", body)
        else:
            self.assertIn(
                "해시 충돌: 같은 칸의 연결 리스트에 3개 키가 있습니다.",
                body,
            )
            self.assertEqual(body.count('class="table-node"'), 3)
            self.assertEqual(body.count('<span class="chain-arrow"> → </span>'), 2)


class LinearProbingServerTests(ServerTests):
    table_class = LinearProbingHashTable


if __name__ == "__main__":
    unittest.main()
