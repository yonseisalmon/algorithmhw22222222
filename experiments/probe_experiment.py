"""Measure separate-chaining lookup costs at several load factors."""

import csv
import math
import random
import string
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable

CAPACITY = 4093
SEED = 2026
ALPHABET = string.ascii_lowercase + string.digits


@dataclass(frozen=True)
class Measurement:
    target_alpha: float
    actual_alpha: float
    entries: int
    successful_measured: float
    successful_theory: float
    unsuccessful_measured: float
    unsuccessful_theory: float


def _random_url(rng: random.Random, host: str, index: int) -> str:
    token = "".join(rng.choices(ALPHABET, k=16))
    return f"https://{host}/{index}-{token}"


def run_experiment() -> list[Measurement]:
    """Run reproducible successful and unsuccessful lookup measurements."""
    rng = random.Random(SEED)
    maximum_entries = 4 * CAPACITY
    successful_urls = [
        _random_url(rng, "stored.example", index)
        for index in range(maximum_entries)
    ]
    unsuccessful_urls = [
        _random_url(rng, "missing.example", index)
        for index in range(maximum_entries)
    ]

    measurements = []
    for quarter in range(1, 17):
        target_alpha = quarter / 4
        entry_count = int(target_alpha * CAPACITY + 0.5)
        alpha = entry_count / CAPACITY
        table = HashTable(capacity=CAPACITY, max_load=None)
        urls = successful_urls[:entry_count]

        for url in urls:
            table.set(url, url)
        if table.capacity != CAPACITY:
            raise RuntimeError("HashTable capacity changed during the experiment")

        successful_queries = urls.copy()
        unsuccessful_queries = unsuccessful_urls[:entry_count].copy()
        rng.shuffle(successful_queries)
        rng.shuffle(unsuccessful_queries)

        successful_comparisons = 0
        for url in successful_queries:
            value, comparisons = table.lookup(url)
            if value != url:
                raise RuntimeError("A stored URL was not found during successful search")
            successful_comparisons += comparisons

        unsuccessful_comparisons = 0
        for url in unsuccessful_queries:
            value, comparisons = table.lookup(url)
            if value is not None:
                raise RuntimeError("An absent URL was found during unsuccessful search")
            unsuccessful_comparisons += comparisons

        measurements.append(
            Measurement(
                target_alpha=target_alpha,
                actual_alpha=alpha,
                entries=entry_count,
                successful_measured=successful_comparisons / entry_count,
                successful_theory=1 + alpha / 2,
                unsuccessful_measured=unsuccessful_comparisons / entry_count,
                unsuccessful_theory=alpha,
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
                "successful_measured",
                "successful_theory",
                "unsuccessful_measured",
                "unsuccessful_theory",
            )
        )
        for result in measurements:
            writer.writerow(
                (
                    f"{result.target_alpha:.2f}",
                    f"{result.actual_alpha:.6f}",
                    result.entries,
                    f"{result.successful_measured:.6f}",
                    f"{result.successful_theory:.6f}",
                    f"{result.unsuccessful_measured:.6f}",
                    f"{result.unsuccessful_theory:.6f}",
                )
            )


def write_svg(measurements: list[Measurement], path: Path) -> None:
    width, height = 900, 560
    left, right, top, bottom = 85, 40, 100, 65
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [
        value
        for result in measurements
        for value in (
            result.successful_measured,
            result.successful_theory,
            result.unsuccessful_measured,
            result.unsuccessful_theory,
        )
    ]
    y_max = max(1, math.ceil(max(values) * 1.1))

    def x_position(alpha: float) -> float:
        return left + alpha / 4 * plot_width

    def y_position(value: float) -> float:
        return top + (y_max - value) / y_max * plot_height

    series = (
        ("성공 탐색 측정", lambda result: result.successful_measured, "#2563eb", ""),
        ("성공 탐색 이론", lambda result: result.successful_theory, "#2563eb", "7 5"),
        ("실패 탐색 측정", lambda result: result.unsuccessful_measured, "#dc2626", ""),
        ("실패 탐색 이론", lambda result: result.unsuccessful_theory, "#dc2626", "7 5"),
    )
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<title>적재율별 해시 테이블 탐색 비교 횟수</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#222">',
        '<text x="450" y="28" text-anchor="middle" font-size="18">적재율별 평균 노드 비교 수</text>',
    ]

    for tick in range(y_max + 1):
        y = y_position(float(tick))
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#ddd"/>'
        )
        lines.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end">{tick}</text>'
        )

    for tick in range(5):
        x = x_position(float(tick))
        lines.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{height - bottom}" stroke="#eee"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{height - bottom + 22}" text-anchor="middle">{tick}</text>'
        )

    lines.extend(
        (
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#222"/>',
            f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="#222"/>',
            f'<text x="{(left + width - right) / 2}" y="{height - 12}" text-anchor="middle">적재율 α</text>',
            f'<text x="18" y="{top + plot_height / 2}" text-anchor="middle" transform="rotate(-90 18 {top + plot_height / 2})">평균 비교 노드 수</text>',
        )
    )

    for index, (label, get_value, color, dash) in enumerate(series):
        points = " ".join(
            f"{x_position(result.actual_alpha):.2f},{y_position(get_value(result)):.2f}"
            for result in measurements
        )
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"{dash_attribute}/>'
        )
        legend_y = 52 + (index // 2) * 20
        legend_x = 170 + (index % 2) * 320
        lines.append(
            f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 28}" y2="{legend_y}" stroke="{color}" stroke-width="2"{dash_attribute}/>'
        )
        lines.append(
            f'<text x="{legend_x + 36}" y="{legend_y + 4}">{label}</text>'
        )

    lines.extend(("</g>", "</svg>"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_table(measurements: list[Measurement]) -> None:
    print(
        "target α | actual α | entries | success measured / theory | "
        "failure measured / theory"
    )
    for result in measurements:
        print(
            f"{result.target_alpha:8.2f} | {result.actual_alpha:8.4f} | "
            f"{result.entries:7d} | {result.successful_measured:8.4f} / "
            f"{result.successful_theory:6.4f} | "
            f"{result.unsuccessful_measured:8.4f} / "
            f"{result.unsuccessful_theory:6.4f}"
        )


def main() -> None:
    measurements = run_experiment()
    output_dir = Path(__file__).resolve().parent
    csv_path = output_dir / "results.csv"
    svg_dir = output_dir / "svg"
    svg_dir.mkdir(parents=True, exist_ok=True)
    svg_path = svg_dir / "probe_experiment.svg"
    write_csv(measurements, csv_path)
    write_svg(measurements, svg_path)
    print(f"Capacity: {CAPACITY}; random seed: {SEED}")
    print_table(measurements)
    print(f"Saved {csv_path}")
    print(f"Saved {svg_path}")


if __name__ == "__main__":
    main()
