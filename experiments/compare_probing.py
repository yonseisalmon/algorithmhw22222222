"""Compare separate chaining and linear probing at matched load factors."""

import csv
import random
import string
import textwrap
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable

CAPACITY = 4093
SEED = 2026
ALPHABET = string.ascii_lowercase + string.digits


@dataclass(frozen=True)
class Measurement:
    target_alpha: float
    actual_alpha: float
    entries: int
    chaining_success_measured: float
    chaining_success_theory: float
    chaining_failure_measured: float
    chaining_failure_theory: float
    linear_success_measured: float
    linear_success_theory: float
    linear_failure_measured: float
    linear_failure_theory: float


def _random_url(rng: random.Random, host: str, index: int) -> str:
    token = "".join(rng.choices(ALPHABET, k=16))
    return f"https://{host}/{index}-{token}"


def _average_cost(table, queries: list[str], expected_values: list[str] | None) -> float:
    total = 0
    for index, query in enumerate(queries):
        value, probes = table.lookup(query)
        expected = expected_values[index] if expected_values is not None else None
        if value != expected:
            raise RuntimeError("Lookup result did not match the expected value")
        total += probes
    return total / len(queries)


def run_experiment(
    capacity: int = CAPACITY, seed: int = SEED
) -> list[Measurement]:
    """Measure both strategies using identical stored and missing URL sets."""
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise TypeError("capacity must be an integer")
    if capacity < 10:
        raise ValueError("capacity must be at least 10")

    rng = random.Random(seed)
    maximum_entries = int(0.9 * capacity + 0.5)
    stored_urls = [
        _random_url(rng, "stored.example", index)
        for index in range(maximum_entries)
    ]
    missing_urls = [
        _random_url(rng, "missing.example", index)
        for index in range(maximum_entries)
    ]

    measurements = []
    for tenths in range(1, 10):
        target_alpha = tenths / 10
        entry_count = int(target_alpha * capacity + 0.5)
        alpha = entry_count / capacity
        urls = stored_urls[:entry_count]
        absent = missing_urls[:entry_count]

        chaining = HashTable(capacity=capacity, max_load=None)
        linear = LinearProbingHashTable(capacity=capacity, max_load=None)
        for url in urls:
            chaining.set(url, url)
            linear.set(url, url)
        if chaining.capacity != capacity or linear.capacity != capacity:
            raise RuntimeError("A table changed capacity during the experiment")

        chain_success = _average_cost(chaining, urls, urls)
        chain_failure = _average_cost(chaining, absent, None)
        linear_success = _average_cost(linear, urls, urls)
        linear_failure = _average_cost(linear, absent, None)
        measurements.append(
            Measurement(
                target_alpha=target_alpha,
                actual_alpha=alpha,
                entries=entry_count,
                chaining_success_measured=chain_success,
                chaining_success_theory=1 + alpha / 2,
                chaining_failure_measured=chain_failure,
                chaining_failure_theory=alpha,
                linear_success_measured=linear_success,
                linear_success_theory=0.5 * (1 + 1 / (1 - alpha)),
                linear_failure_measured=linear_failure,
                linear_failure_theory=0.5 * (1 + 1 / (1 - alpha) ** 2),
            )
        )
    return measurements


def write_csv(measurements: list[Measurement], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            (
                "target_alpha",
                "actual_alpha",
                "entries",
                "chaining_success_measured",
                "chaining_success_theory",
                "chaining_failure_measured",
                "chaining_failure_theory",
                "linear_success_measured",
                "linear_success_theory",
                "linear_failure_measured",
                "linear_failure_theory",
            )
        )
        for result in measurements:
            writer.writerow(
                (
                    f"{result.target_alpha:.2f}",
                    f"{result.actual_alpha:.6f}",
                    result.entries,
                    f"{result.chaining_success_measured:.6f}",
                    f"{result.chaining_success_theory:.6f}",
                    f"{result.chaining_failure_measured:.6f}",
                    f"{result.chaining_failure_theory:.6f}",
                    f"{result.linear_success_measured:.6f}",
                    f"{result.linear_success_theory:.6f}",
                    f"{result.linear_failure_measured:.6f}",
                    f"{result.linear_failure_theory:.6f}",
                )
            )


def _svg_text(x: float, y: float, value: str, **attributes: str) -> str:
    attrs = " ".join(f'{name.replace("_", "-")}="{value}"' for name, value in attributes.items())
    return f'<text x="{x:.2f}" y="{y:.2f}" {attrs}>{value}</text>'


def write_svg(measurements: list[Measurement], path: Path) -> None:
    width, height = 1000, 700
    plot_left, plot_right = 95, 35
    plot_width = width - plot_left - plot_right
    panels = (
        (
            "성공 탐색 평균 검사 횟수",
            "success",
            6.0,
            110,
            250,
        ),
        (
            "실패 탐색 평균 검사 횟수",
            "failure",
            55.0,
            405,
            250,
        ),
    )
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<title>선형 탐지와 개별 체이닝 탐색 비용 비교</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" font-size="12" fill="#222">',
        _svg_text(width / 2, 34, "적재율별 해시 테이블 평균 탐색 비용", text_anchor="middle", font_size="20"),
    ]
    series = (
        ("개별 체이닝 측정", "chaining", "measured", "#2563eb", ""),
        ("개별 체이닝 이론", "chaining", "theory", "#2563eb", "7 5"),
        ("선형 탐지 측정", "linear", "measured", "#dc2626", ""),
        ("선형 탐지 이론", "linear", "theory", "#dc2626", "7 5"),
    )

    for title, metric, y_max, top, panel_height in panels:
        bottom = top + panel_height
        plot_top = top + 52
        plot_bottom = bottom - 30
        plot_height = plot_bottom - plot_top
        lines.append(_svg_text(plot_left, top + 15, title, font_size="15", font_weight="bold"))

        def x_position(alpha: float) -> float:
            return plot_left + (alpha - 0.1) / 0.8 * plot_width

        def y_position(value: float) -> float:
            return plot_bottom - value / y_max * plot_height

        tick_count = 6 if metric == "success" else 5
        for tick in range(tick_count + 1):
            value = y_max * tick / tick_count
            y = y_position(value)
            lines.append(
                f'<line x1="{plot_left}" y1="{y:.2f}" x2="{width - plot_right}" y2="{y:.2f}" stroke="#ddd"/>'
            )
            lines.append(
                _svg_text(plot_left - 10, y + 4, f"{value:.0f}", text_anchor="end")
            )
        for tenth in range(1, 10, 2):
            alpha = tenth / 10
            x = x_position(alpha)
            lines.append(
                f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" y2="{plot_bottom}" stroke="#eee"/>'
            )
            lines.append(
                _svg_text(x, plot_bottom + 20, f"{alpha:.1f}", text_anchor="middle")
            )
        lines.extend(
            (
                f'<line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" y2="{plot_bottom}" stroke="#222"/>',
                f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{width - plot_right}" y2="{plot_bottom}" stroke="#222"/>',
            )
        )

        for index, (label, strategy, theory, color, dash) in enumerate(series):
            attribute = f' stroke-dasharray="{dash}"' if dash else ""
            field = f"{strategy}_{metric}_{theory}"
            points = " ".join(
                f"{x_position(result.actual_alpha):.2f},{y_position(getattr(result, field)):.2f}"
                for result in measurements
            )
            lines.append(
                f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"{attribute}/>'
            )
            legend_x = plot_left + index * 205
            legend_y = top + 38
            lines.append(
                f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 25}" y2="{legend_y}" stroke="{color}" stroke-width="2"{attribute}/>'
            )
            lines.append(
                _svg_text(legend_x + 31, legend_y + 4, label)
            )

    lines.extend(("</g>", "</svg>"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_text(
    commands: list[str], x: float, y: float, value: str, size: float = 10, bold: bool = False
) -> None:
    font = "F2" if bold else "F1"
    commands.append(
        f"BT /{font} {size:.1f} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm "
        f"({_pdf_escape(value)}) Tj ET"
    )


def _pdf_line(
    commands: list[str],
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    color: tuple[float, float, float] = (0, 0, 0),
    width: float = 0.8,
    dashed: bool = False,
) -> None:
    red, green, blue = color
    dash = "[4 3] 0 d" if dashed else "[] 0 d"
    commands.append(
        f"{red:.3f} {green:.3f} {blue:.3f} RG {width:.2f} w {dash} "
        f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S"
    )


def _pdf_plot(
    commands: list[str],
    measurements: list[Measurement],
    metric: str,
    title: str,
    y_max: float,
    bottom: float,
) -> None:
    left, width, height = 68.0, 480.0, 158.0
    top = bottom + height
    plot_top = top - 30
    plot_bottom = bottom + 22
    plot_height = plot_bottom - plot_top
    _pdf_text(commands, left, top + 13, title, 11, bold=True)

    colors = {
        "chaining": (0.12, 0.29, 0.80),
        "linear": (0.80, 0.12, 0.12),
    }

    def x_position(alpha: float) -> float:
        return left + (alpha - 0.1) / 0.8 * width

    def y_position(value: float) -> float:
        return plot_bottom - value / y_max * plot_height

    tick_count = 5
    for tick in range(tick_count + 1):
        value = y_max * tick / tick_count
        y = y_position(value)
        _pdf_line(commands, left, y, left + width, y, (0.83, 0.83, 0.83), 0.4)
        _pdf_text(commands, left - 28, y - 3, f"{value:.0f}", 7)
    for tenth in range(1, 10, 2):
        alpha = tenth / 10
        x = x_position(alpha)
        _pdf_line(commands, x, plot_top, x, plot_bottom, (0.90, 0.90, 0.90), 0.4)
        _pdf_text(commands, x - 6, bottom + 8, f"{alpha:.1f}", 7)
    _pdf_line(commands, left, plot_top, left, plot_bottom)
    _pdf_line(commands, left, plot_bottom, left + width, plot_bottom)

    legend = (
        ("Chain measured", "chaining", "measured", False),
        ("Chain theory", "chaining", "theory", True),
        ("Linear measured", "linear", "measured", False),
        ("Linear theory", "linear", "theory", True),
    )
    for index, (label, strategy, kind, dashed) in enumerate(legend):
        legend_x = left + index * 122
        _pdf_line(
            commands,
            legend_x,
            top - 9,
            legend_x + 18,
            top - 9,
            colors[strategy],
            1.2,
            dashed,
        )
        _pdf_text(commands, legend_x + 21, top - 12, label, 7)
        field = f"{strategy}_{metric}_{kind}"
        previous = None
        for result in measurements:
            point = (x_position(result.actual_alpha), y_position(getattr(result, field)))
            if previous is not None:
                _pdf_line(
                    commands, previous[0], previous[1], point[0], point[1],
                    colors[strategy], 1.3, dashed
                )
            previous = point


def _make_pdf(pages: list[bytes]) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 7 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 8 0 R >>",
    ]
    for page in pages:
        objects.append(
            b"<< /Length " + str(len(page)).encode("ascii") + b" >>\nstream\n"
            + page
            + b"\nendstream"
        )
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def write_pdf(measurements: list[Measurement], path: Path) -> None:
    chain_success_error = max(
        abs(item.chaining_success_measured - item.chaining_success_theory)
        for item in measurements
    )
    chain_failure_error = max(
        abs(item.chaining_failure_measured - item.chaining_failure_theory)
        for item in measurements
    )
    linear_success_error = max(
        abs(item.linear_success_measured - item.linear_success_theory)
        for item in measurements
    )
    linear_failure_error = max(
        abs(item.linear_failure_measured - item.linear_failure_theory)
        for item in measurements
    )
    final = measurements[-1]

    first_page = []
    _pdf_text(first_page, 48, 748, "Linear Probing vs Separate Chaining", 20, bold=True)
    _pdf_text(first_page, 48, 728, "Lookup-cost experiment | 2-page report", 11)
    _pdf_text(first_page, 48, 690, "Question and method", 14, bold=True)
    paragraphs = (
        "Both tables store the same deterministic URL keys at each load factor. "
        "Capacity is 4093, the random seed is 2026, and alpha ranges from 0.1 to 0.9. "
        "For each point, every stored key is searched once and an equally sized set "
        "of absent URLs is searched once.",
        "A successful cost counts occupied nodes or slots inspected through the matching "
        "key. An unsuccessful linear-probing cost also includes the terminating empty "
        "slot; chaining counts the key comparisons in its bucket list.",
        "Separate-chaining references: successful = 1 + alpha/2; unsuccessful = alpha. "
        "Linear-probing references: successful = 0.5*(1 + 1/(1-alpha)); "
        "unsuccessful = 0.5*(1 + 1/(1-alpha)^2). These are expected-cost estimates "
        "under uniform hashing assumptions; linear probing is affected by primary clustering.",
    )
    y = 670
    for paragraph in paragraphs:
        for line in textwrap.wrap(paragraph, width=92):
            _pdf_text(first_page, 48, y, line, 9.5)
            y -= 13
        y -= 9

    _pdf_text(first_page, 48, y, "Results and interpretation", 14, bold=True)
    y -= 22
    summary = (
        f"Maximum absolute measured-vs-theory error: chaining hit {chain_success_error:.3f}, "
        f"miss {chain_failure_error:.3f}; linear hit {linear_success_error:.3f}, "
        f"miss {linear_failure_error:.3f} probes.",
        f"At alpha={final.actual_alpha:.3f}, unsuccessful linear probing measured "
        f"{final.linear_failure_measured:.2f} slots versus theoretical "
        f"{final.linear_failure_theory:.2f} (a {final.linear_failure_theory - final.linear_failure_measured:.2f} "
        f"lower result); chaining measured {final.chaining_failure_measured:.2f} versus "
        f"{final.chaining_failure_theory:.2f}. The linear miss cost is still about "
        f"{final.linear_failure_measured / final.chaining_failure_measured:.0f}x chaining. "
        "The gap from the estimate reflects this finite deterministic sample and the "
        "idealized uniform-hashing assumptions.",
        "The full nine-point measurements are in linear_probing_comparison.csv. "
        "The next page plots measured values against their theoretical references.",
    )
    for paragraph in summary:
        for line in textwrap.wrap(paragraph, width=92):
            _pdf_text(first_page, 48, y, line, 9.5)
            y -= 13
        y -= 9
    _pdf_text(first_page, 48, 38, "Reproducible command: make compare", 9, bold=True)

    second_page = []
    _pdf_text(second_page, 48, 752, "Measured and theoretical lookup costs", 17, bold=True)
    _pdf_plot(second_page, measurements, "success", "Successful search", 6, 525)
    _pdf_plot(second_page, measurements, "failure", "Unsuccessful search", 55, 300)
    _pdf_text(second_page, 48, 260, "Selected measured / theoretical values", 10, bold=True)
    headers = (
        ("alpha", 48),
        ("chain hit", 100),
        ("linear hit", 180),
        ("chain miss", 282),
        ("linear miss", 390),
    )
    for label, x in headers:
        _pdf_text(second_page, x, 244, label, 7.5, bold=True)
    for row_index, target in enumerate((0.1, 0.5, 0.9)):
        item = min(measurements, key=lambda result: abs(result.target_alpha - target))
        y_row = 228 - row_index * 14
        values = (
            (f"{item.actual_alpha:.2f}", 48),
            (f"{item.chaining_success_measured:.2f}/{item.chaining_success_theory:.2f}", 100),
            (f"{item.linear_success_measured:.2f}/{item.linear_success_theory:.2f}", 180),
            (f"{item.chaining_failure_measured:.2f}/{item.chaining_failure_theory:.2f}", 282),
            (f"{item.linear_failure_measured:.2f}/{item.linear_failure_theory:.2f}", 390),
        )
        for value, x in values:
            _pdf_text(second_page, x, y_row, value, 7.5)
    _pdf_text(
        second_page,
        48,
        176,
        "CSV: experiments/linear_probing_comparison.csv | SVG: experiments/svg/linear_probing_comparison.svg",
        8,
    )
    pdf = _make_pdf(
        [
            "\n".join(first_page).encode("ascii"),
            "\n".join(second_page).encode("ascii"),
        ]
    )
    path.write_bytes(pdf)


def print_table(measurements: list[Measurement]) -> None:
    print(
        "alpha | chain hit M/T | chain miss M/T | "
        "linear hit M/T | linear miss M/T"
    )
    for item in measurements:
        print(
            f"{item.actual_alpha:5.3f} | "
            f"{item.chaining_success_measured:6.3f}/{item.chaining_success_theory:6.3f} | "
            f"{item.chaining_failure_measured:6.3f}/{item.chaining_failure_theory:6.3f} | "
            f"{item.linear_success_measured:6.3f}/{item.linear_success_theory:6.3f} | "
            f"{item.linear_failure_measured:6.3f}/{item.linear_failure_theory:6.3f}"
        )


def main() -> None:
    measurements = run_experiment()
    output_dir = Path(__file__).resolve().parent
    svg_dir = output_dir / "svg"
    svg_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "linear_probing_comparison.csv"
    svg_path = svg_dir / "linear_probing_comparison.svg"
    pdf_path = output_dir / "linear_probing_report.pdf"
    write_csv(measurements, csv_path)
    write_svg(measurements, svg_path)
    write_pdf(measurements, pdf_path)
    print(f"Capacity: {CAPACITY}; random seed: {SEED}; entries per alpha: rounded(alpha * capacity)")
    print_table(measurements)
    print(f"Saved {csv_path}")
    print(f"Saved {svg_path}")
    print(f"Saved {pdf_path}")


if __name__ == "__main__":
    main()
