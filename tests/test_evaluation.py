from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import naibbe_habit_evaluate as evaluate_habit
from evaluation_metrics import (
    METRIC_NAMES,
    DistanceCalibration,
    sha256_text,
    wrap_tokens,
)


class PaperFixtureTests(unittest.TestCase):
    def test_four_source_parts_are_valid_and_have_paper_composite_hash(self) -> None:
        plaintext = evaluate_habit.load_paper_plaintext()
        self.assertEqual(len(plaintext), 32_000)
        self.assertEqual(
            sha256_text(plaintext), evaluate_habit.FIXTURE_SHA256
        )
        self.assertTrue(plaintext.isascii())
        self.assertTrue(plaintext.isalpha())
        self.assertTrue(plaintext.islower())

    def test_token_wrapping_has_ten_tokens_per_complete_line(self) -> None:
        rendered = wrap_tokens([f"t{i}" for i in range(23)])
        lines = rendered.splitlines()
        self.assertEqual([len(line.split()) for line in lines], [10, 10, 3])
        self.assertEqual(rendered.split(), [f"t{i}" for i in range(23)])


class DistanceCalibrationTests(unittest.TestCase):
    def test_published_naibbe_distances_are_reproduced(self) -> None:
        frame = pd.read_csv(evaluate_habit.CALIBRATION_CSV)
        calibration = DistanceCalibration.from_csv()
        distances = calibration.distances(frame)
        naibbe = frame["text"].str.startswith("Naibbe -")
        values = distances[naibbe.to_numpy()]
        first = frame.index[frame["text"] == "Naibbe - 52_01"][0]
        self.assertAlmostEqual(distances[first], 4.722103321596108)
        self.assertAlmostEqual(float(values.mean()), 4.9236283635560145)

    def test_metric_order_is_the_calibration_order(self) -> None:
        frame = pd.read_csv(evaluate_habit.CALIBRATION_CSV, nrows=1)
        self.assertEqual(frame.columns.tolist(), ["text", *METRIC_NAMES])

    def test_historical_stats_script_is_unchanged(self) -> None:
        path = (
            evaluate_habit.REPO_ROOT
            / "figure_utils"
            / "gaskell_bowern_2022"
            / "stats.py"
        )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "b9de53c1cf26858355ab27d08a4740ed1fd96ad0f03208b0f07db1d9cb67303d",
        )


class GenerationTests(unittest.TestCase):
    def test_seeded_generation_is_reproducible_and_paper_formatted(self) -> None:
        with tempfile.TemporaryDirectory() as first_temp, tempfile.TemporaryDirectory() as second_temp:
            kwargs = {"seeds": [1], "p_values": [0.0], "decks": [52]}
            first = evaluate_habit.generate_habit_texts(Path(first_temp), **kwargs)[0]
            second = evaluate_habit.generate_habit_texts(Path(second_temp), **kwargs)[0]
            self.assertEqual(first.ciphertext_sha256, second.ciphertext_sha256)
            self.assertEqual(first.n_tokens, second.n_tokens)
            lines = first.path.read_text(encoding="utf-8").splitlines()
            self.assertTrue(all(len(line.split()) == 10 for line in lines[:-1]))
            self.assertLessEqual(len(lines[-1].split()), 10)

    def test_bootstrap_interval_is_deterministic(self) -> None:
        first = evaluate_habit.bootstrap_mean_ci([1.0, 2.0, 3.0], seed=7)
        second = evaluate_habit.bootstrap_mean_ci([1.0, 2.0, 3.0], seed=7)
        np.testing.assert_array_equal(first, second)


class EvaluationArtifactTests(unittest.TestCase):
    def test_full_result_matrix_is_complete(self) -> None:
        result_dir = (
            evaluate_habit.REPO_ROOT
            / "figure_utils"
            / "habit_evaluation"
            / "results"
        )
        runs = pd.read_csv(result_dir / "runs.csv")
        summary = pd.read_csv(result_dir / "summary.csv")
        deltas = pd.read_csv(result_dir / "metric_deltas.csv")
        self.assertEqual(runs.shape, (100, 54))
        self.assertEqual(summary.shape, (15, 13))
        self.assertEqual(deltas.shape, (378, 9))
        self.assertFalse(runs.drop(columns=["p_habit"]).isna().any().any())
        self.assertEqual(
            runs.groupby("model").size().to_dict(),
            {"greshko_published": 20, "habit": 80},
        )


if __name__ == "__main__":
    unittest.main()
