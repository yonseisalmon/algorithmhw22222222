"""HTTP server for the URL shortener."""

import argparse
from functools import partial
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable
from src.shortener import Shortener

MAX_FORM_BYTES = 1_000_000
SERVER_TABLE_CAPACITY = 64
DEMO_URLS = (
    "https://example.com/demo-by",
    "https://example.com/demo-kb",
    "https://example.com/demo-md",
)


def _seed_demo_data(shortener: Shortener) -> None:
    for url in DEMO_URLS:
        shortener.shorten(url)


class ShortenerHandler(BaseHTTPRequestHandler):
    """Render the shortener form, redirects, and hash-table inspection page."""

    def __init__(self, *args, shortener: Shortener, **kwargs) -> None:
        self.shortener = shortener
        super().__init__(*args, **kwargs)

    def _send_page(self, status: int, title: str, content: str) -> None:
        page = (
            '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f"<title>{escape(title)}</title></head><body>"
            '<nav><a href="/">URL 단축</a> | <a href="/table">해시 테이블</a></nav>'
            f"<main><h1>{escape(title)}</h1>{content}</main></body></html>"
        )
        body = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _short_path(code: str) -> str:
        return f"/{code}"

    def _render_hash_details(
        self,
        url: str,
        steps: tuple[int, ...],
        bucket_index: int,
        probe_slots: tuple[int, ...] = (),
    ) -> str:
        items = []
        previous = 0
        for index, (character, value) in enumerate(zip(url, steps), start=1):
            calculation = (
                f"h{index} = ({previous} * 31 + ord({character!r})) "
                f"% {self.shortener.table_capacity} = {value}"
            )
            items.append(f"<li><code>{escape(calculation)}</code></li>")
            previous = value
        probe_details = ""
        if probe_slots:
            path = " → ".join(str(index) for index in probe_slots)
            collision_note = ""
            if len(probe_slots) > 1:
                collision_note = (
                    "<p>해시 충돌: 시작 칸이 점유되어 다음 칸을 탐사했습니다.</p>"
                )
            probe_details = (
                f"{collision_note}<p>선형 탐사 경로: <code>{path}</code></p>"
            )
        return (
            "<details><summary>호너 해시 계산 과정 보기</summary>"
            f"<p>h0 = 0; 시작 칸 = {bucket_index}</p>{probe_details}"
            f"<ol>{''.join(items)}</ol></details>"
        )

    def _table_page(self) -> str:
        buckets = self.shortener.inspect_table()
        rows = []
        linear_probing = self.shortener.table_strategy == "linear_probing"
        strategy_name = "선형 탐지" if linear_probing else "개별 체이닝"
        for bucket_index, chain in enumerate(buckets):
            nodes = []
            for url, code in chain:
                steps, calculated_index = self.shortener.hash_trace(url)
                short_path = self._short_path(code)
                probe_slots = (
                    self.shortener.probe_trace(url) if linear_probing else ()
                )
                details = self._render_hash_details(
                    url, steps, calculated_index, probe_slots
                )
                nodes.append(
                    '<section class="table-node">'
                    f"<p>URL 키: <code>{escape(url)}</code></p>"
                    f"<p>짧은 코드: <code>{escape(code)}</code></p>"
                    f'<p>짧은 링크: <a href="/{escape(code, quote=True)}">'
                    f"{escape(short_path)}</a></p>{details}</section>"
                )
            if nodes:
                if linear_probing:
                    chain_html = "".join(nodes)
                else:
                    collision_note = ""
                    if len(chain) > 1:
                        collision_note = (
                            f"<p>해시 충돌: 같은 칸의 연결 리스트에 "
                            f"{len(chain)}개 키가 있습니다.</p>"
                        )
                    chain_html = (
                        f'<div class="chain">{collision_note}'
                        + '<span class="chain-arrow"> → </span>'.join(nodes)
                        + "</div>"
                    )
            else:
                chain_html = "<p>비어 있음</p>"
            rows.append(
                f'<li><strong>칸 {bucket_index}</strong>{chain_html}</li>'
            )
        return (
            f"<p>충돌 처리: {strategy_name}</p>"
            f"<p>용량: {self.shortener.table_capacity}</p>"
            f"<ol>{''.join(rows)}</ol>"
        )

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self._send_page(
                200,
                "URL 단축",
                '<form action="/shorten" method="post">'
                '<label for="url">원본 URL</label> '
                '<input id="url" name="url" type="url" required '
                'placeholder="https://example.com/"> '
                '<button type="submit">줄이기</button></form>',
            )
            return

        if path == "/table":
            self._send_page(200, "현재 해시 테이블", self._table_page())
            return

        if path.startswith("/") and path.count("/") == 1 and len(path) > 1:
            code = path[1:]
            try:
                url = self.shortener.expand(code)
            except (KeyError, ValueError):
                self._send_page(404, "찾을 수 없음", "<p>발급된 링크가 아닙니다.</p>")
                return

            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self._send_page(404, "찾을 수 없음", "<p>페이지가 없습니다.</p>")

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/shorten":
            self._send_page(404, "찾을 수 없음", "<p>페이지가 없습니다.</p>")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_page(400, "잘못된 요청", "<p>요청 본문을 읽을 수 없습니다.</p>")
            return
        if content_length <= 0 or content_length > MAX_FORM_BYTES:
            self._send_page(400, "잘못된 요청", "<p>요청 본문 크기가 잘못되었습니다.</p>")
            return

        try:
            form_body = self.rfile.read(content_length).decode("utf-8")
            form = parse_qs(form_body, keep_blank_values=True, max_num_fields=16)
        except (UnicodeDecodeError, ValueError):
            self._send_page(400, "잘못된 요청", "<p>폼 데이터를 읽을 수 없습니다.</p>")
            return

        urls = form.get("url")
        if not urls:
            self._send_page(400, "잘못된 URL", "<p>URL을 입력해 주세요.</p>")
            return

        url = urls[0]
        try:
            code = self.shortener.shorten(url)
        except (TypeError, ValueError):
            self._send_page(400, "잘못된 URL", "<p>유효한 HTTP 또는 HTTPS URL을 입력해 주세요.</p>")
            return

        short_path = self._short_path(code)
        content = (
            f"<p>원본 URL: <code>{escape(url)}</code></p>"
            f'<p>짧은 링크: <a href="/{escape(code, quote=True)}">'
            f"{escape(short_path)}</a></p>"
            '<p><a href="/">다른 URL 줄이기</a></p>'
        )
        self._send_page(200, "줄이기 완료", content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--strategy", choices=("chaining", "linear"), default="chaining"
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    table_class = (
        LinearProbingHashTable if args.strategy == "linear" else HashTable
    )
    shortener = Shortener(
        table_class=partial(table_class, capacity=SERVER_TABLE_CAPACITY)
    )
    _seed_demo_data(shortener)
    handler = partial(ShortenerHandler, shortener=shortener)
    with ThreadingHTTPServer(("", args.port), handler) as server:
        print(
            f"Serving {args.strategy} URL shortener on "
            f"http://0.0.0.0:{args.port}"
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
