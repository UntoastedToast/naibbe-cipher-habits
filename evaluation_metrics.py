"""Reproducible adapters for the Naibbe habit evaluation.

The 42 linguistic metrics remain implemented in ``stats_habit.py``, a clearly
documented deterministic derivative of the unchanged Gaskell and Bowern script
used by Greshko. This module supplies its Python interface, the paper's frozen
42-dimensional distance, and the existing RMSF Hurst calculation used here.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent
GASKELL_SCRIPT = (
    REPO_ROOT / "figure_utils" / "gaskell_bowern_2022" / "stats_habit.py"
)
CALIBRATION_CSV = (
    REPO_ROOT
    / "figure_utils"
    / "gaskell_bowern_2022"
    / "results"
    / "metrics_enciphered.csv"
)

METRIC_NAMES = [
    "wordlen_mean", "wordlen_std", "wordlen_skew",
    "wordlen_unique_mean", "wordlen_unique_std", "wordlen_unique_skew",
    "wordlen_autocorr",
    "wordunique_mean", "wordunique_std", "wordunique_skew",
    "wordchange_mean", "wordchange_std", "wordchange_skew",
    "worddist_max", "worddist_shape",
    "wordbias_mean", "wordbias_std", "wordbias_skew",
    "wordbias_lines_mean", "wordbias_lines_std", "wordbias_lines_skew",
    "chardist_max", "chardist_shape",
    "ngramdist_max", "ngramdist_shape",
    "charbias_mean", "charbias_std", "charbias_skew",
    "charbias_words_mean", "charbias_words_std", "charbias_words_skew",
    "unique_words", "repeated_words", "tripled_words",
    "unique_chars", "repeated_chars", "tripled_chars",
    "unique_ngrams", "entropy", "compression", "zipf", "flipped_pairs",
]

MAX_BITS = 500_000
WINDOW_SIZES = np.unique(
    np.logspace(1.3, np.log10(MAX_BITS // 10), num=20, dtype=int)
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wrap_tokens(tokens: Sequence[str], width: int = 10) -> str:
    """Return whitespace-separated tokens with a stable number per line."""
    if width < 1:
        raise ValueError("width must be at least one")
    return "\n".join(
        " ".join(tokens[start : start + width])
        for start in range(0, len(tokens), width)
    ) + ("\n" if tokens else "")


def run_gaskell_metrics(
    files: Iterable[Path],
    output_csv: Path,
    *,
    seed: int = 2025,
    subset_iterations: int = 100,
    subset_words: int = 200,
) -> pd.DataFrame:
    """Run the documented deterministic 42-metric derivative for several files."""
    paths = [Path(path).resolve() for path in files]
    if not paths:
        raise ValueError("at least one input file is required")
    output_csv = Path(output_csv).resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(GASKELL_SCRIPT),
        "--seed", str(seed),
        "--subset-iterations", str(subset_iterations),
        "--subset-words", str(subset_words),
        "--output", str(output_csv),
        *map(str, paths),
    ]
    subprocess.run(command, cwd=REPO_ROOT, check=True)
    result = pd.read_csv(output_csv)
    expected = ["text", *METRIC_NAMES]
    if result.columns.tolist() != expected:
        raise ValueError(
            "Gaskell metric columns differ from the published 42-column order"
        )
    return result


@dataclass(frozen=True)
class DistanceCalibration:
    """Frozen paper calibration for distance to Voynichese EVA Basic."""

    mean: np.ndarray
    sample_std: np.ndarray
    reference_z: np.ndarray

    @classmethod
    def from_csv(cls, path: Path = CALIBRATION_CSV) -> "DistanceCalibration":
        frame = pd.read_csv(path)
        if frame.columns.tolist() != ["text", *METRIC_NAMES]:
            raise ValueError("calibration CSV does not contain the expected metrics")
        values = frame[METRIC_NAMES].to_numpy(dtype=float)
        reference_rows = frame.index[frame["text"] == "Voynichese - EVA Basic"]
        if len(reference_rows) != 1:
            raise ValueError("calibration must contain one EVA Basic reference")
        mean = values.mean(axis=0)
        sample_std = values.std(axis=0, ddof=1)
        reference_z = (values[reference_rows[0]] - mean) / sample_std
        return cls(mean=mean, sample_std=sample_std, reference_z=reference_z)

    def z_scores(self, frame: pd.DataFrame) -> np.ndarray:
        return (
            frame[METRIC_NAMES].to_numpy(dtype=float) - self.mean
        ) / self.sample_std

    def distances(self, frame: pd.DataFrame) -> np.ndarray:
        differences = self.z_scores(frame) - self.reference_z
        return np.sqrt(np.square(differences).sum(axis=1))

    def absolute_metric_gaps(self, frame: pd.DataFrame) -> np.ndarray:
        return np.abs(self.z_scores(frame) - self.reference_z)


def text_to_binary(text: str) -> str:
    """Encode alphabetic text using the project's 5-bit RMSF encoding."""
    normalized = unicodedata.normalize("NFKD", text)
    letters = "".join(char for char in normalized if char.isalpha()).lower()
    rank_map = {
        char: format(index + 1, "05b")
        for index, char in enumerate("abcdefghijklmnopqrstuvwxyz")
    }
    return "".join(rank_map.get(char, "") for char in letters)


def hurst_metrics(text: str) -> dict[str, float | int]:
    """Calculate Hurst and crossover exactly as the checked-in notebook does."""
    binary = text_to_binary(text)[:MAX_BITS]
    if len(binary) <= int(WINDOW_SIZES[-1]) + 1:
        raise ValueError("text is too short for the configured RMSF windows")
    walk = np.cumsum(np.fromiter(
        (1 if bit == "1" else -1 for bit in binary), dtype=np.int64
    ))
    fluctuations = []
    for window in WINDOW_SIZES:
        differences = walk[window:] - walk[:-window]
        variance = np.mean(differences ** 2) - np.mean(differences) ** 2
        fluctuations.append(float(np.sqrt(max(variance, 0))))
    log_windows = np.log10(WINDOW_SIZES)
    log_fluctuations = np.log10(np.asarray(fluctuations))
    hurst = round(float(np.polyfit(log_windows, log_fluctuations, 1)[0]), 3)
    crossover_index = int(np.argmax(np.diff(log_fluctuations / log_windows)))
    return {
        "hurst": hurst,
        "crossover_n": int(WINDOW_SIZES[crossover_index]),
        "n_bits": len(binary),
    }
