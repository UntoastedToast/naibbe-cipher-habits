"""Run the paper-compatible evaluation of the Naibbe habit extension."""

from __future__ import annotations

import argparse
import os
import random
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, cast

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike

import naibbe_habit
from evaluation_metrics import (
    CALIBRATION_CSV,
    METRIC_NAMES,
    DistanceCalibration,
    hurst_metrics,
    run_gaskell_metrics,
    sha256_text,
    wrap_tokens,
)


REPO_ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = REPO_ROOT / "figure_utils" / "habit_evaluation" / "data"
FIXTURE_PARTS = [
    ("dante_8000.txt", "e3fdb47bf611b53d5478e433c13b4aa92e3713add8e149e90a7735bc15112c49"),
    ("de_sphaera_8000.txt", "05ade4d609df85afcfb1e7f3c00dc0fe1b700eb190f66f197fa6e47dc036dbfc"),
    ("alchemical_herbal_8000.txt", "141c3cd47201bd341680df6ade8d04475fc848f84b010262fe1916b2d2d5ad7e"),
    ("pliny_book16_8000.txt", "fef9a1dac4c4382bad1aa2284d749e3f225fb9c1cc251a1277fee7f490cb0cf1"),
]
REFERENCE_DIR = (
    REPO_ROOT / "figure_utils" / "gaskell_bowern_2022" / "data" / "naibbe"
)
DEFAULT_OUTPUT_DIR = REPO_ROOT / "figure_utils" / "habit_evaluation" / "results"
FIXTURE_SHA256 = "e6f005cc3d1b5610006cb7241e9f9928671ab98e00db6ffbdf95de6e8be2bfe8"
VOYNICH_B_HURST = 0.677


@dataclass(frozen=True)
class EvaluationText:
    text: str
    path: Path
    model: str
    configuration: str
    deck: int
    p_habit: float | None
    seed: int
    n_tokens: int
    ciphertext_sha256: str


def load_paper_plaintext(directory: Path = FIXTURE_DIR) -> str:
    parts = []
    for filename, expected_sha256 in FIXTURE_PARTS:
        part = (directory / filename).read_text(encoding="utf-8").strip()
        if len(part) != 8_000:
            raise ValueError(f"{filename} must contain 8,000 letters, got {len(part)}")
        if sha256_text(part) != expected_sha256:
            raise ValueError(f"{filename} SHA-256 does not match its provenance record")
        parts.append(part)
    plaintext = "".join(parts)
    if len(plaintext) != 32_000:
        raise ValueError(f"paper fixture must contain 32,000 letters, got {len(plaintext)}")
    if not plaintext.isascii() or not plaintext.isalpha() or not plaintext.islower():
        raise ValueError("paper fixture must contain lowercase ASCII letters only")
    if sha256_text(plaintext) != FIXTURE_SHA256:
        raise ValueError("paper fixture SHA-256 does not match its provenance record")
    return plaintext


def p_label(value: float) -> str:
    return str(value).replace(".", "p")


def generate_habit_texts(
    directory: Path,
    *,
    seeds: Sequence[int],
    p_values: Sequence[float],
    decks: Sequence[int],
) -> list[EvaluationText]:
    """Generate paired habit texts, sharing one respacing per plaintext seed."""
    plaintext = load_paper_plaintext()
    generated: list[EvaluationText] = []
    for seed in seeds:
        ngrams = naibbe_habit._respace_with_rng(
            plaintext, random.Random(seed)
        )
        if "".join(ngrams) != plaintext:
            raise AssertionError("respacing changed the paper plaintext")
        for deck in decks:
            for p_habit in p_values:
                tokens, _ = naibbe_habit.encrypt_naibbe_habit(
                    plaintext,
                    naibbe_habit.naibbe_tables,
                    naibbe_habit.placeholder_to_glyph,
                    use_78=deck == 78,
                    bifolia_per_quire=4,
                    tokens_per_page=160,
                    p_habit=p_habit,
                    rng=random.Random(seed),
                    ngrams=ngrams,
                )
                stem = (
                    f"habit_p{p_label(p_habit)}_deck{deck}_seed{seed:02d}"
                )
                rendered = wrap_tokens(tokens, width=10)
                path = directory / f"{stem}.txt"
                path.write_text(rendered, encoding="utf-8", newline="\n")
                generated.append(EvaluationText(
                    text=stem,
                    path=path,
                    model="habit",
                    configuration=f"p={p_habit:g}",
                    deck=deck,
                    p_habit=p_habit,
                    seed=seed,
                    n_tokens=len(tokens),
                    ciphertext_sha256=sha256_text(rendered),
                ))
    return generated


def published_reference_texts() -> list[EvaluationText]:
    references = []
    for path in sorted(REFERENCE_DIR.glob("*_10_word_lines.txt")):
        run_name = path.name.removesuffix("_10_word_lines.txt")
        nominal_deck, run = run_name.split("_")
        deck = 52 if nominal_deck == "52" else 78
        rendered = path.read_text(encoding="utf-8")
        references.append(EvaluationText(
            text=path.stem,
            path=path,
            model="greshko_published",
            configuration="Greshko published",
            deck=deck,
            p_habit=None,
            seed=int(run),
            n_tokens=len(rendered.split()),
            ciphertext_sha256=sha256_text(rendered),
        ))
    if len(references) != 20:
        raise ValueError(f"expected 20 published Naibbe texts, found {len(references)}")
    return references


def bootstrap_mean_ci(
    values: ArrayLike, *, seed: int, iterations: int = 10_000
) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(array, size=(iterations, len(array)), replace=True)
    means = samples.mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def summarize_runs(runs: pd.DataFrame, bootstrap_seed: int) -> pd.DataFrame:
    frames = [runs.assign(deck_group=runs["deck"].astype(str))]
    frames.append(runs.assign(deck_group="both"))
    combined = pd.concat(frames, ignore_index=True)
    rows = []
    group_columns = ["model", "configuration", "p_habit", "deck_group"]
    for group_index, (keys, group) in enumerate(
        combined.groupby(group_columns, dropna=False, sort=True)
    ):
        model, configuration, p_habit, deck_group = keys
        row = {
            "model": model,
            "configuration": configuration,
            "p_habit": p_habit,
            "deck": deck_group,
            "n_runs": len(group),
        }
        for metric_index, column in enumerate(("hurst", "distance_eva_basic")):
            values = group[column].to_numpy(dtype=float)
            low, high = bootstrap_mean_ci(
                values,
                seed=bootstrap_seed + 100 * group_index + metric_index,
            )
            row.update({
                f"{column}_mean": float(values.mean()),
                f"{column}_std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                f"{column}_ci_low": low,
                f"{column}_ci_high": high,
            })
        rows.append(row)
    return pd.DataFrame(rows)


def calculate_metric_deltas(
    runs: pd.DataFrame,
    calibration: DistanceCalibration,
    bootstrap_seed: int,
) -> pd.DataFrame:
    habit = runs[runs["model"] == "habit"].copy()
    gaps = calibration.absolute_metric_gaps(habit)
    for index, metric in enumerate(METRIC_NAMES):
        habit[f"gap_{metric}"] = gaps[:, index]

    rows = []
    comparison_index = 0
    for deck in [52, 78, "both"]:
        deck_frame = habit if deck == "both" else habit[habit["deck"] == deck]
        control = deck_frame[deck_frame["p_habit"] == 0.0].set_index(
            ["deck", "seed"]
        )
        for p_habit in sorted(deck_frame["p_habit"].dropna().unique()):
            if p_habit == 0.0:
                continue
            treatment = deck_frame[deck_frame["p_habit"] == p_habit].set_index(
                ["deck", "seed"]
            )
            common = control.index.intersection(treatment.index)
            for metric_index, metric in enumerate(METRIC_NAMES):
                deltas = (
                    treatment.loc[common, f"gap_{metric}"].to_numpy()
                    - control.loc[common, f"gap_{metric}"].to_numpy()
                )
                low, high = bootstrap_mean_ci(
                    deltas,
                    seed=(
                        bootstrap_seed
                        + 10_000
                        + 100 * comparison_index
                        + metric_index
                    ),
                )
                mean = float(deltas.mean())
                rows.append({
                    "deck": str(deck),
                    "p_habit": p_habit,
                    "metric": metric,
                    "n_pairs": len(deltas),
                    "mean_gap_delta": mean,
                    "std_gap_delta": (
                        float(deltas.std(ddof=1)) if len(deltas) > 1 else 0.0
                    ),
                    "ci_low": low,
                    "ci_high": high,
                    "direction": "worse" if mean > 0 else "better",
                })
            comparison_index += 1
    return pd.DataFrame(rows)


def write_plots(
    runs: pd.DataFrame, metric_deltas: pd.DataFrame, output_dir: Path
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 6))
    published = runs[runs["model"] == "greshko_published"]
    ax.scatter(
        published["distance_eva_basic"], published["hurst"],
        color="0.55", marker="x", label="Greshko published", alpha=0.8,
    )
    colors = {0.0: "#4c78a8", 0.3: "#59a14f", 0.5: "#f28e2b", 1.0: "#e15759"}
    markers = {52: "o", 78: "s"}
    habit = runs[runs["model"] == "habit"]
    for keys, group in habit.groupby(["p_habit", "deck"]):
        p_habit, deck = cast(tuple[float, int], keys)
        ax.scatter(
            group["distance_eva_basic"], group["hurst"],
            color=colors.get(float(p_habit)), marker=markers[int(deck)],
            label=f"p={p_habit:g}, deck={deck}", alpha=0.75,
        )
    ax.axhline(VOYNICH_B_HURST, color="black", linestyle="--", linewidth=1,
               label=f"Voynich B H={VOYNICH_B_HURST:.3f}")
    ax.set_xlabel("42-metric distance to EVA Basic (lower is closer)")
    ax.set_ylabel("RMSF Hurst exponent")
    ax.set_title("Naibbe habit trade-off: linguistic distance vs. Hurst")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(output_dir / "distance_hurst.svg")
    plt.close(fig)

    combined = metric_deltas[metric_deltas["deck"] == "both"].pivot(
        index="p_habit", columns="metric", values="mean_gap_delta"
    ).reindex(columns=METRIC_NAMES)
    limit = float(np.nanmax(np.abs(combined.to_numpy()))) or 1.0
    fig, ax = plt.subplots(figsize=(18, 4.5))
    image = ax.imshow(
        combined.to_numpy(), aspect="auto", cmap="RdBu_r", vmin=-limit, vmax=limit
    )
    ax.set_yticks(range(len(combined.index)), [f"p={p:g}" for p in combined.index])
    ax.set_xticks(range(len(METRIC_NAMES)), METRIC_NAMES, rotation=90, fontsize=7)
    ax.set_title("Change in absolute metric gap to EVA Basic versus p=0")
    fig.colorbar(image, ax=ax, label="positive = worse, negative = better")
    fig.tight_layout()
    fig.savefig(output_dir / "metric_deltas.svg")
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Naibbe habit runs with Greshko's 42-metric method."
    )
    parser.add_argument('--seeds', type=int, nargs='+', default=list(range(1, 11)))
    parser.add_argument(
        '--p-habit', type=float, nargs='+', default=[0.0, 0.3, 0.5, 1.0]
    )
    parser.add_argument('--decks', type=int, nargs='+', default=[52, 78])
    parser.add_argument('--metric-seed', type=int, default=2025)
    parser.add_argument('--bootstrap-seed', type=int, default=2025)
    parser.add_argument('--subset-iterations', type=int, default=100)
    parser.add_argument('--subset-words', type=int, default=200)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--keep-ciphertexts', action='store_true')
    parser.add_argument('--skip-plots', action='store_true')
    return parser


def validate_arguments(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if not args.seeds or len(set(args.seeds)) != len(args.seeds):
        parser.error('--seeds must contain distinct values')
    if any(value < 0.0 or value > 1.0 for value in args.p_habit):
        parser.error('--p-habit values must be in [0, 1]')
    if 0.0 not in args.p_habit:
        parser.error('--p-habit must include 0 for the paired control')
    if set(args.decks) - {52, 78}:
        parser.error('--decks accepts only 52 and 78')


def run_evaluation(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="naibbe-habit-") as temporary:
        temporary_dir = Path(temporary)
        generated = generate_habit_texts(
            temporary_dir,
            seeds=args.seeds,
            p_values=args.p_habit,
            decks=args.decks,
        )
        references = published_reference_texts()
        texts = [*references, *generated]
        raw_metrics_path = output_dir / "metrics_raw.csv"
        metrics = run_gaskell_metrics(
            [item.path for item in texts],
            raw_metrics_path,
            seed=args.metric_seed,
            subset_iterations=args.subset_iterations,
            subset_words=args.subset_words,
        )
        metadata = pd.DataFrame([
            {
                "text": item.text,
                "model": item.model,
                "configuration": item.configuration,
                "deck": item.deck,
                "p_habit": item.p_habit,
                "seed": item.seed,
                "n_tokens": item.n_tokens,
                "ciphertext_sha256": item.ciphertext_sha256,
                **hurst_metrics(item.path.read_text(encoding="utf-8")),
            }
            for item in texts
        ])
        runs = metadata.merge(metrics, on="text", how="inner", validate="one_to_one")
        calibration = DistanceCalibration.from_csv(CALIBRATION_CSV)
        runs["distance_eva_basic"] = calibration.distances(runs)
        runs = runs.sort_values(
            ["model", "p_habit", "deck", "seed"], na_position="first"
        ).reset_index(drop=True)
        summary = summarize_runs(runs, args.bootstrap_seed)
        metric_deltas = calculate_metric_deltas(
            runs, calibration, args.bootstrap_seed
        )

        runs.to_csv(
            output_dir / "runs.csv", index=False, float_format="%.10g", lineterminator="\n"
        )
        summary.to_csv(
            output_dir / "summary.csv", index=False, float_format="%.10g", lineterminator="\n"
        )
        metric_deltas.to_csv(
            output_dir / "metric_deltas.csv", index=False,
            float_format="%.10g", lineterminator="\n",
        )
        if args.keep_ciphertexts:
            ciphertext_dir = output_dir / "ciphertexts"
            ciphertext_dir.mkdir(exist_ok=True)
            for item in generated:
                shutil.copy2(item.path, ciphertext_dir / item.path.name)
        if not args.skip_plots:
            os.environ["MPLCONFIGDIR"] = str(temporary_dir / "matplotlib")
            write_plots(runs, metric_deltas, output_dir)
    return runs, summary, metric_deltas


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_arguments(args, parser)
    runs, _, _ = run_evaluation(args)
    print(
        f"Evaluated {len(runs)} texts; results written to "
        f"{args.output_dir.resolve()}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
