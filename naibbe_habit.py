# Copyright (c) 2025, Michael A. Greshko
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software, datasets, and associated documentation files (the "Software
# and Datasets"), to deal in the Software and Datasets without restriction,
# including without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software and Datasets, and to
# permit persons to whom the Software is furnished to do so, subject to the
# following conditions:
#
# - The above copyright notice and this permission notice shall be included
#   in all copies or substantial portions of the Software and Datasets.
# - Any publications making use of the Software and Datasets, or any substantial
#   portions thereof, shall cite the Software and Datasets's original publication:
#
# > Greshko, Michael A. (2025). The Naibbe cipher: a substitution cipher that
#   encrypts Latin and Italian as Voynich Manuscript-like ciphertext.
#   Cryptologia. https://doi.org/10.1080/01611194.2025.2566408
#
# THE SOFTWARE AND DATASETS ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
# EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE AND DATASETS.

"""Bifolium-based scribal-habit extension of the Naibbe cipher.

This script grew out of a question raised by Greshko (2025, section 4.2). If a
scribe worked on one bifolium at a time and developed local preferences while
doing so, traces of that work might appear far apart once the sheets were
folded and read as a codex. The experiment below tries out one fairly simple
version of this idea.

Most of the encryption procedure still comes from ``naibbe_v2``. The plaintext
is respaced in the usual way and assigned to pages in reading order. During
encryption, however, the four pages of a bifolium are handled together. Each
non-empty bifolium receives a favourite substitution table, which is consulted
with probability ``p_habit``. The ordinary Naibbe deck is used for the other
draws. Afterwards, the pages are put back into reading order.

The bifolia are worked from the outside of a quire towards its centre. This is
a practical choice for the experiment. ``p_habit=0`` provides the control,
while ``p_habit=1`` represents the strongest form of the table preference.
Four bifolia per quire are used as the standard Voynich layout, giving eight
folios or sixteen written pages. Irregular quires and foldouts are left for a
later model. See Zyats et al. (2016, pp. 23-37) and
https://www.voynich.nu/descr.html.

References
----------
Michael A. Greshko (2025), "The Naibbe cipher: a substitution cipher that
encrypts Latin and Italian as Voynich Manuscript-like ciphertext",
Cryptologia, section 4.2. https://doi.org/10.1080/01611194.2025.2566408

Paula Zyats et al. (2016), "Physical Findings", in Raymond Clemens (ed.),
The Voynich Manuscript, pp. 23-37. New Haven: Yale University Press.

Rene Zandbergen, "Description of the Voynich MS".
https://www.voynich.nu/descr.html
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import io
import os
import random
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

# "Habit extension" marks behavior added around the naibbe_v2 core.

# V2 core: load the original mappings from their repository-relative CSV.
_REPO_ROOT = Path(__file__).resolve().parent
_PREVIOUS_CWD = Path.cwd()
try:
    os.chdir(_REPO_ROOT)
    with contextlib.redirect_stdout(io.StringIO()):
        import naibbe_v2
finally:
    os.chdir(_PREVIOUS_CWD)


# === Parameters, card weights, and glyph mappings ===
# V2 core: keep the original public data and helpers available here.
ALPHABET = naibbe_v2.ALPHABET
TABLES = naibbe_v2.TABLES
CARD_WEIGHTS = naibbe_v2.CARD_WEIGHTS
naibbe_tables = naibbe_v2.naibbe_tables
placeholder_to_glyph = naibbe_v2.placeholder_to_glyph
create_card_deck = naibbe_v2.create_card_deck
respace_plaintext = naibbe_v2.respace_plaintext
clean_line = naibbe_v2.clean_line
respace_line = naibbe_v2.respace_line
UNAMBIGUOUS = naibbe_v2.UNAMBIGUOUS
MAX_BIGRAM_RETRIES = naibbe_v2.MAX_BIGRAM_RETRIES
USE_78_CARD_DECK = naibbe_v2.USE_78_CARD_DECK
SPACE_REMOVAL_RATE = naibbe_v2.SPACE_REMOVAL_RATE
RESPACING = naibbe_v2.RESPACING
encrypt_naibbe = naibbe_v2.encrypt_naibbe


# Habit extension: map reading-order pages to their physical bifolia.
def _validate_layout_index(value: int, upper: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    if not 0 <= value < upper:
        raise ValueError(f"{name} must be in [0, {upper}), got {value}")


def _page_to_bifolio(page: int, n_bifolia: int) -> tuple[int, int]:
    """Map a zero-based reading-order page to its bifolium and local page.

    A quire of ``n`` nested bifolia has ``4*n`` pages. Bifolium ``k`` owns
    pages ``2*k``, ``2*k+1``, ``4*n-2*k-2``, and ``4*n-2*k-1``. Local page
    values 0/1 are the recto/verso of its first folio and 2/3 those of its
    second folio.
    """
    if not isinstance(n_bifolia, int) or isinstance(n_bifolia, bool):
        raise TypeError(
            "n_bifolia must be an integer, "
            f"got {type(n_bifolia).__name__}"
        )
    if n_bifolia < 1:
        raise ValueError(f"n_bifolia must be >= 1, got {n_bifolia}")
    _validate_layout_index(page, 4 * n_bifolia, "page")

    if page < 2 * n_bifolia:
        return page // 2, page % 2

    offset = page - 2 * n_bifolia
    return n_bifolia - 1 - offset // 2, 2 + offset % 2


def _bifolio_to_page(
    bifolio: int, page_in_bifolio: int, n_bifolia: int
) -> int:
    """Return the reading-order page for a page on a nested bifolium."""
    if not isinstance(n_bifolia, int) or isinstance(n_bifolia, bool):
        raise TypeError(
            "n_bifolia must be an integer, "
            f"got {type(n_bifolia).__name__}"
        )
    if n_bifolia < 1:
        raise ValueError(f"n_bifolia must be >= 1, got {n_bifolia}")
    _validate_layout_index(bifolio, n_bifolia, "bifolio")
    _validate_layout_index(page_in_bifolio, 4, "page_in_bifolio")

    if page_in_bifolio < 2:
        return 2 * bifolio + page_in_bifolio
    return 4 * n_bifolia - 2 * bifolio - 2 + (page_in_bifolio - 2)


def bifolio_page_indices(bifolio: int, n_bifolia: int) -> tuple[int, ...]:
    """Return one bifolium's four pages in folio reading order."""
    return tuple(
        _bifolio_to_page(bifolio, local_page, n_bifolia)
        for local_page in range(4)
    )


# === Deck creation ===
# V2 core: use the same weighted deck with the experiment's RNG.
def _new_deck(use_78: bool, rng: random.Random) -> list[str]:
    """Create a Naibbe table-selection deck using the supplied RNG."""
    deck = [
        table
        for table, count in CARD_WEIGHTS[use_78].items()
        for _ in range(count)
    ]
    rng.shuffle(deck)
    return deck


def _next_table(
    deck: list[str],
    deck_index: int,
    use_78: bool,
    rng: random.Random,
) -> tuple[str, list[str], int]:
    """Draw a table, reshuffling a full deck only after it is exhausted."""
    if deck_index >= len(deck):
        deck = _new_deck(use_78, rng)
        deck_index = 0
    table = deck[deck_index]
    return table, deck, deck_index + 1


# Habit extension: keep one weighted table preference per bifolium.
def _choose_favorite_table(use_78: bool, rng: random.Random) -> str:
    """Choose a bifolium's favourite table from the base Naibbe weights.

    Favourite selections and normal deck selections therefore have the same
    marginal distribution. ``p_habit`` changes local clustering without
    changing the expected global table ratios. Ambiguity redraws are the only
    exception because they deliberately bypass the habit.
    """
    weights = CARD_WEIGHTS[use_78]
    return str(
        rng.choices(
            tuple(weights.keys()),
            weights=tuple(weights.values()),
            k=1,
        )[0]
    )


def _select_table(
    deck: list[str],
    deck_index: int,
    use_78: bool,
    rng: random.Random,
    favorite_table: str | None,
    p_habit: float,
    *,
    allow_habit: bool = True,
) -> tuple[str, list[str], int]:
    """Use the favourite table or continue with the normal card deck."""
    if allow_habit and favorite_table is not None:
        use_favorite = p_habit == 1.0 or (
            p_habit > 0.0 and rng.random() < p_habit
        )
        if use_favorite:
            return favorite_table, deck, deck_index
    return _next_table(deck, deck_index, use_78, rng)


# === Respacing ===
# V2 core: apply standard respacing with the experiment's RNG.
def _respace_with_rng(
    text: str,
    rng: random.Random,
    pre_plaintext_file: TextIO | None = None,
) -> list[str]:
    """Apply the original standard respacing rule with a local RNG."""
    compact = text.lower().replace(" ", "")
    output: list[str] = []
    index = 0
    while index < len(compact):
        if index == len(compact) - 1 or rng.random() < RESPACING / 36:
            output.append(compact[index])
            index += 1
        else:
            output.append(compact[index : index + 2])
            index += 2

    if pre_plaintext_file is not None:
        pre_plaintext_file.write(" ".join(output) + "\n")
    return output


# === Ambiguity-safe bigram handling ===
# V2 core: rebuild the collision indexes for caller-provided mappings.
def _build_ambiguity_catalog(
    tables: dict,
    glyph_map: dict,
) -> tuple[set[str], dict[str, set[tuple[str, str]]]]:
    """Build ambiguity indexes for the actual tables passed by the caller."""
    unigram_glyphs: set[str] = set()
    prefixes: list[tuple[str, str]] = []
    suffixes: list[tuple[str, str]] = []

    for table_name in TABLES:
        for letter in ALPHABET:
            unigram_code = tables[table_name][("unigram", letter)]
            prefix_code = tables[table_name][("prefix", letter)]
            suffix_code = tables[table_name][("suffix", letter)]
            unigram_glyphs.add(glyph_map.get(unigram_code, unigram_code))
            prefixes.append((prefix_code, glyph_map.get(prefix_code, prefix_code)))
            suffixes.append((suffix_code, glyph_map.get(suffix_code, suffix_code)))

    catalog: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for prefix_code, prefix_glyph in prefixes:
        for suffix_code, suffix_glyph in suffixes:
            catalog[prefix_glyph + suffix_glyph].add(
                (prefix_code, suffix_code)
            )
    return unigram_glyphs, dict(catalog)


# === Encryption ===
# V2 core: retain unigram and ambiguity-safe bigram encryption.
def _draw_bigram(
    first_letter: str,
    second_letter: str,
    tables: dict,
    glyph_map: dict,
    use_78: bool,
    deck: list[str],
    deck_index: int,
    rng: random.Random,
    favorite_table: str | None,
    p_habit: float,
    unigram_glyphs: set[str],
    bigram_catalog: dict[str, set[tuple[str, str]]],
) -> tuple[str, list[str], int, int]:
    """Encrypt a bigram and redraw any ambiguous result."""
    retries = 0
    for attempt in range(MAX_BIGRAM_RETRIES if UNAMBIGUOUS else 1):
        # Habit extension: retries fall back to the normal card deck.
        allow_habit = attempt == 0
        prefix_table, deck, deck_index = _select_table(
            deck,
            deck_index,
            use_78,
            rng,
            favorite_table,
            p_habit,
            allow_habit=allow_habit,
        )
        prefix_code = tables[prefix_table][("prefix", first_letter)]
        prefix_glyph = glyph_map.get(prefix_code, prefix_code)

        suffix_table, deck, deck_index = _select_table(
            deck,
            deck_index,
            use_78,
            rng,
            favorite_table,
            p_habit,
            allow_habit=allow_habit,
        )
        suffix_code = tables[suffix_table][("suffix", second_letter)]
        suffix_glyph = glyph_map.get(suffix_code, suffix_code)
        combined = prefix_glyph + suffix_glyph

        if not UNAMBIGUOUS:
            return combined, deck, deck_index, retries
        # Reject collisions with a unigram glyph.
        if combined in unigram_glyphs:
            retries += 1
            continue
        # Reject collisions with another prefix/suffix pair.
        possible_pairs = bigram_catalog.get(combined, set())
        if any(
            pair != (prefix_code, suffix_code) for pair in possible_pairs
        ):
            retries += 1
            continue
        return combined, deck, deck_index, retries

    raise RuntimeError(
        "Unable to produce an unambiguous bigram after "
        f"{MAX_BIGRAM_RETRIES} attempts"
    )


def _draw_token(
    plaintext_token: str,
    tables: dict,
    glyph_map: dict,
    use_78: bool,
    deck: list[str],
    deck_index: int,
    rng: random.Random,
    favorite_table: str | None,
    p_habit: float,
    unigram_glyphs: set[str],
    bigram_catalog: dict[str, set[tuple[str, str]]],
) -> tuple[str, list[str], int, int]:
    if len(plaintext_token) == 1:
        table, deck, deck_index = _select_table(
            deck,
            deck_index,
            use_78,
            rng,
            favorite_table,
            p_habit,
        )
        code = tables[table][("unigram", plaintext_token)]
        return glyph_map.get(code, code), deck, deck_index, 0
    if len(plaintext_token) == 2:
        return _draw_bigram(
            plaintext_token[0],
            plaintext_token[1],
            tables,
            glyph_map,
            use_78,
            deck,
            deck_index,
            rng,
            favorite_table,
            p_habit,
            unigram_glyphs,
            bigram_catalog,
        )
    raise ValueError(
        "Naibbe plaintext tokens must contain one or two letters, "
        f"got {plaintext_token!r}"
    )


# Habit extension: encrypt one physical bifolium under a local preference.
def _encrypt_bifolio(
    plaintext_tokens: list[str],
    tables: dict,
    glyph_map: dict,
    use_78: bool,
    deck: list[str],
    deck_index: int,
    favorite_table: str | None,
    p_habit: float,
    rng: random.Random,
    unigram_glyphs: set[str],
    bigram_catalog: dict[str, set[tuple[str, str]]],
) -> tuple[list[str], list[str], int, int]:
    """Encrypt one bifolium under a local favourite-table habit."""
    ciphertext: list[str] = []
    retries_total = 0

    for plaintext_token in plaintext_tokens:
        encrypted, deck, deck_index, retries = _draw_token(
            plaintext_token,
            tables,
            glyph_map,
            use_78,
            deck,
            deck_index,
            rng,
            favorite_table,
            p_habit,
            unigram_glyphs,
            bigram_catalog,
        )
        ciphertext.append(encrypted)
        retries_total += retries

    return ciphertext, deck, deck_index, retries_total


def _validate_model_parameters(
    bifolia_per_quire: int,
    tokens_per_page: int,
    p_habit: float,
) -> None:
    if (
        not isinstance(bifolia_per_quire, int)
        or isinstance(bifolia_per_quire, bool)
        or bifolia_per_quire < 1
    ):
        raise ValueError(
            "bifolia_per_quire must be a positive integer, "
            f"got {bifolia_per_quire!r}"
        )
    if (
        not isinstance(tokens_per_page, int)
        or isinstance(tokens_per_page, bool)
        or tokens_per_page < 1
    ):
        raise ValueError(
            "tokens_per_page must be a positive integer, "
            f"got {tokens_per_page!r}"
        )
    if isinstance(p_habit, bool) or not isinstance(p_habit, (int, float)):
        raise TypeError(
            "p_habit must be a number in [0, 1], "
            f"got {type(p_habit).__name__}"
        )
    if not 0.0 <= p_habit <= 1.0:
        raise ValueError(f"p_habit must be in [0, 1], got {p_habit}")


# Habit extension: process bifolia, then restore final reading order.
def encrypt_naibbe_habit(
    plaintext: str,
    tables: dict,
    glyph_map: dict,
    use_78: bool = False,
    bifolia_per_quire: int = 4,
    tokens_per_page: int = 160,
    p_habit: float = 0.5,
    pre_plaintext_file: TextIO | None = None,
    rng: random.Random | None = None,
    ngrams: list[str] | None = None,
) -> tuple[list[str], int]:
    """Encrypt text with a bifolium-local favourite-table habit.

    At the start of each non-empty bifolium, a favourite table is selected from
    the base Naibbe weights. ``p_habit`` is the probability of consulting that
    table instead of drawing the next card. Zero is a no-habit control; one is
    the maximal habit model.

    The card deck is continuous over the complete encryption and is reshuffled
    only when exhausted, as specified for the base Naibbe cipher. A partial
    final quire is padded with empty pages to the configured physical quire
    size, preventing its page pairs from being silently remapped.

    The supplied ``rng`` controls respacing, favourite selection, habit choices,
    and all deck shuffles, so a fresh ``random.Random(seed)`` reproduces a run
    without mutating module-global random state.
    """
    _validate_model_parameters(
        bifolia_per_quire, tokens_per_page, p_habit
    )
    if not isinstance(plaintext, str):
        raise TypeError(
            f"plaintext must be str, got {type(plaintext).__name__}"
        )
    if rng is None:
        rng = random.Random()
    if not isinstance(use_78, bool):
        raise TypeError(
            f"use_78 must be bool, got {type(use_78).__name__}"
        )

    if ngrams is None:
        plaintext_tokens = _respace_with_rng(
            plaintext, rng, pre_plaintext_file
        )
    else:
        plaintext_tokens = list(ngrams)
        if pre_plaintext_file is not None:
            pre_plaintext_file.write(" ".join(plaintext_tokens) + "\n")

    if not plaintext_tokens:
        return [], 0
    for token in plaintext_tokens:
        if (
            not isinstance(token, str)
            or len(token) not in (1, 2)
            or any(letter not in ALPHABET for letter in token)
        ):
            raise ValueError(
                "ngrams must contain one or two lowercase Naibbe letters, "
                f"got {token!r}"
            )
    compact_plaintext = plaintext.lower().replace(" ", "")
    if ngrams is not None and "".join(plaintext_tokens) != compact_plaintext:
        raise ValueError(
            "Concatenated ngrams must equal plaintext after lowercasing and "
            "removing spaces"
        )

    unigram_glyphs, bigram_catalog = _build_ambiguity_catalog(
        tables, glyph_map
    )
    page_count = 4 * bifolia_per_quire
    quire_token_count = page_count * tokens_per_page
    quires = [
        plaintext_tokens[start : start + quire_token_count]
        for start in range(0, len(plaintext_tokens), quire_token_count)
    ]

    deck = _new_deck(use_78, rng)
    deck_index = 0
    all_ciphertext: list[str] = []
    total_retries = 0

    for quire_tokens in quires:
        pages = [
            quire_tokens[start : start + tokens_per_page]
            for start in range(0, len(quire_tokens), tokens_per_page)
        ]
        pages.extend([] for _ in range(page_count - len(pages)))
        encrypted_pages: list[list[str] | None] = [None] * page_count

        for bifolio in range(bifolia_per_quire):
            reading_pages = bifolio_page_indices(
                bifolio, bifolia_per_quire
            )
            bifolio_tokens = [
                token
                for page in reading_pages
                for token in pages[page]
            ]
            favorite_table = (
                _choose_favorite_table(use_78, rng)
                if bifolio_tokens and p_habit > 0.0
                else None
            )

            encrypted, deck, deck_index, retries = _encrypt_bifolio(
                bifolio_tokens,
                tables,
                glyph_map,
                use_78,
                deck,
                deck_index,
                favorite_table,
                float(p_habit),
                rng,
                unigram_glyphs,
                bigram_catalog,
            )
            total_retries += retries

            offset = 0
            for page in reading_pages:
                token_count = len(pages[page])
                encrypted_pages[page] = encrypted[
                    offset : offset + token_count
                ]
                offset += token_count

        for page in encrypted_pages:
            if page:
                all_ciphertext.extend(page)

    return all_ciphertext, total_retries


# === Line-by-line file encryption and optional respacing ===
# Habit extension: segment the cleaned plaintext once across source lines.
def iter_encrypted_lines(
    input_path: str | os.PathLike[str],
    use_78: bool,
    bifolia_per_quire: int,
    tokens_per_page: int,
    p_habit: float,
    rng: random.Random,
    pre_plaintext_file: TextIO | None = None,
) -> Iterator[tuple[str, list[str], int]]:
    """Yield cleaned input lines with their reading-order ciphertext tokens.

    The input is cleaned and respaced once as a continuous plaintext. This
    matches the paper's removal of original spacing and avoids introducing an
    artificial unigram at every source-file line ending. A bigram spanning an
    input-line boundary is assigned to the line containing its first letter.
    """
    with open(input_path, "r", encoding="utf-8") as input_file:
        cleaned_lines = [clean_line(line) for line in input_file]

    full_plaintext = "".join(cleaned_lines)
    plaintext_tokens = _respace_with_rng(
        full_plaintext, rng, pre_plaintext_file
    )
    encrypted_tokens, total_retries = encrypt_naibbe_habit(
        full_plaintext,
        naibbe_tables,
        placeholder_to_glyph,
        use_78=use_78,
        bifolia_per_quire=bifolia_per_quire,
        tokens_per_page=tokens_per_page,
        p_habit=p_habit,
        rng=rng,
        ngrams=plaintext_tokens,
    )

    character_to_line = [
        line_index
        for line_index, line in enumerate(cleaned_lines)
        for _ in line
    ]
    line_token_counts = [0] * len(cleaned_lines)
    character_index = 0
    for token in plaintext_tokens:
        if character_index < len(character_to_line):
            line_token_counts[character_to_line[character_index]] += 1
        character_index += len(token)

    token_index = 0
    retries_reported = False
    for cleaned, token_count in zip(cleaned_lines, line_token_counts):
        line_tokens = encrypted_tokens[
            token_index : token_index + token_count
        ]
        token_index += token_count
        retries = total_retries if line_tokens and not retries_reported else 0
        retries_reported = retries_reported or bool(line_tokens)
        yield cleaned, line_tokens, retries


# === Randomly remove spaces in output ===
# V2 core: use the same rule with the experiment's RNG.
def _remove_spaces(
    line: str, drop_rate: float, rng: random.Random
) -> str:
    tokens = line.strip().split()
    if len(tokens) < 2 or drop_rate <= 0:
        return line.strip()
    if drop_rate >= 1:
        return "".join(tokens)

    output = tokens[0]
    for token in tokens[1:]:
        output += token if rng.random() < drop_rate else " " + token
    return output


# === Command-line interface ===
def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="naibbe-habit",
        description=(
            "Operationalize the bifolium-based scribal habit discussed in "
            "Greshko's section 4.2: encrypt one bifolium at a time and "
            "favour one substitution table while working on it."
        ),
    )
    parser.add_argument(
        "--input",
        default="input/examples/nathist_book16.txt",
        help="Path to the input plaintext file.",
    )
    parser.add_argument(
        "--output",
        default="encrypted/nathist_output_ciphertext_bigram_unambig.txt",
        help="Path to the ciphertext output file.",
    )
    parser.add_argument(
        "--respaced-output",
        default=(
            "encrypted/"
            "nathist_output_ciphertext_respaced_bigram_unambig.txt"
        ),
        help="Path to the ciphertext output with occasional spaces removed.",
    )
    parser.add_argument(
        "--pre-plaintext-output",
        default=(
            "respaced_plaintext/"
            "nathist_pre_encryption_respaced_plaintext_bigram_unambig.txt"
        ),
        help="Path to the respaced plaintext token sequence.",
    )
    deck_group = parser.add_mutually_exclusive_group()
    deck_group.add_argument(
        "--use-78",
        dest="use_78",
        action="store_true",
        help="Use the 78-card Naibbe deck.",
    )
    deck_group.add_argument(
        "--use-52",
        dest="use_78",
        action="store_false",
        help="Use the 52-card Naibbe deck.",
    )
    parser.set_defaults(use_78=USE_78_CARD_DECK)
    parser.add_argument(
        "--bifolia-per-quire",
        type=int,
        default=4,
        help=(
            "Physical quire size in bifolia (default: 4, the standard "
            "Voynich Manuscript quire)."
        ),
    )
    parser.add_argument(
        "--tokens-per-page",
        type=int,
        default=160,
        help="Experimental fixed page capacity in tokens (default: 160).",
    )
    parser.add_argument(
        "--p-habit",
        dest="p_habit",
        type=float,
        default=0.5,
        help=(
            "Probability of using the bifolium's favourite table instead of "
            "drawing the next card (default: 0.5)."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed controlling respacing, table habits, and deck shuffles.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments strictly so misspellings fail loudly."""
    return build_parser().parse_args(argv)


def _ensure_parent(path: str | os.PathLike[str]) -> None:
    Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)


def main(argv: list[str] | None = None) -> None:
    """Encrypt a file with the bifolium-local habit model."""
    args = parse_args(argv)
    _validate_model_parameters(
        args.bifolia_per_quire, args.tokens_per_page, args.p_habit
    )
    rng = random.Random(args.seed)

    for path in (
        args.output,
        args.respaced_output,
        args.pre_plaintext_output,
    ):
        _ensure_parent(path)

    with (
        open(args.output, "w", encoding="utf-8") as output_file,
        open(args.respaced_output, "w", encoding="utf-8") as respaced_file,
        open(
            args.pre_plaintext_output, "w", encoding="utf-8"
        ) as pre_plaintext_file,
    ):
        total_retries = 0
        for cleaned, tokens, retries in iter_encrypted_lines(
            args.input,
            args.use_78,
            args.bifolia_per_quire,
            args.tokens_per_page,
            args.p_habit,
            rng,
            pre_plaintext_file,
        ):
            total_retries += retries
            if not cleaned:
                output_file.write("\n")
                respaced_file.write("\n")
                continue
            line = " ".join(tokens)
            output_file.write(line + "\n")
            respaced_file.write(
                _remove_spaces(line, SPACE_REMOVAL_RATE, rng) + "\n"
            )

    # === Print ambiguity count ===
    print(f"Total ambiguity retries: {total_retries}")
    print(
        "Habit model: "
        f"bifolia_per_quire={args.bifolia_per_quire}, "
        f"tokens_per_page={args.tokens_per_page}, "
        f"p_habit={args.p_habit}, "
        f"deck={78 if args.use_78 else 52}, "
        f"seed={args.seed}"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
