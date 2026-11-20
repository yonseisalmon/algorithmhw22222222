import re
import tempfile
import unittest
from pathlib import Path

from experiments.compare_probing import run_experiment, write_pdf


class ProbingComparisonTests(unittest.TestCase):
    def test_experiment_compares_both_tables_at_nine_load_factors(self):
        measurements = run_experiment(capacity=100, seed=7)

        self.assertEqual(len(measurements), 9)
        self.assertEqual(
            [item.target_alpha for item in measurements],
            [tenths / 10 for tenths in range(1, 10)],
        )
        self.assertEqual(
            [item.entries for item in measurements],
            [10, 20, 30, 40, 50, 60, 70, 80, 90],
        )
        for item in measurements:
            alpha = item.actual_alpha
            self.assertAlmostEqual(item.chaining_success_theory, 1 + alpha / 2)
            self.assertAlmostEqual(item.chaining_failure_theory, alpha)
            self.assertAlmostEqual(
                item.linear_success_theory,
                0.5 * (1 + 1 / (1 - alpha)),
            )
            self.assertAlmostEqual(
                item.linear_failure_theory,
                0.5 * (1 + 1 / (1 - alpha) ** 2),
            )

    def test_report_pdf_has_exactly_two_pages(self):
        measurements = run_experiment(capacity=100, seed=11)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            write_pdf(measurements, path)
            pdf = path.read_bytes()

        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertEqual(len(re.findall(rb"/Type /Page\b", pdf)), 2)


if __name__ == "__main__":
    unittest.main()
