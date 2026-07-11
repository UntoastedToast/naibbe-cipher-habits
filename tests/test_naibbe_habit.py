from __future__ import annotations

import inspect
import random
import unittest
from contextlib import nullcontext
from unittest import mock

import decrypt_naibbe
import naibbe_habit


def make_unambiguous_tables() -> tuple[dict, dict]:
    tables: dict[str, dict[tuple[str, str], str]] = {}
    glyph_map: dict[str, str] = {}
    state_markers = {
        "unigram": "U",
        "prefix": "P",
        "suffix": "S",
    }
    for table in naibbe_habit.TABLES:
        table_entries: dict[tuple[str, str], str] = {}
        for state, marker in state_markers.items():
            for letter in naibbe_habit.ALPHABET:
                code = f"{marker}[{table}:{letter}]"
                table_entries[(state, letter)] = code
                glyph_map[code] = code
        tables[table] = table_entries
    return tables, glyph_map


class PageLayoutTests(unittest.TestCase):
    def test_nested_bifolia_have_expected_reading_order_pages(self) -> None:
        self.assertEqual(
            naibbe_habit.bifolio_page_indices(0, 3), (0, 1, 10, 11)
        )
        self.assertEqual(
            naibbe_habit.bifolio_page_indices(1, 3), (2, 3, 8, 9)
        )
        self.assertEqual(
            naibbe_habit.bifolio_page_indices(2, 3), (4, 5, 6, 7)
        )

    def test_page_mapping_is_bijective(self) -> None:
        for n_bifolia in range(1, 9):
            mapped_pages = set()
            for page in range(4 * n_bifolia):
                bifolio, local_page = naibbe_habit._page_to_bifolio(
                    page, n_bifolia
                )
                round_trip = naibbe_habit._bifolio_to_page(
                    bifolio, local_page, n_bifolia
                )
                self.assertEqual(round_trip, page)
                mapped_pages.add((bifolio, local_page))
            self.assertEqual(len(mapped_pages), 4 * n_bifolia)

    def test_invalid_layout_indices_fail(self) -> None:
        with self.assertRaises(ValueError):
            naibbe_habit._page_to_bifolio(4, 1)
        with self.assertRaises(ValueError):
            naibbe_habit._bifolio_to_page(1, 0, 1)


class HabitEncryptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tables, self.glyph_map = make_unambiguous_tables()
        self.deck = list(naibbe_habit.TABLES)

    def encrypt(
        self,
        ngrams: list[str],
        *,
        favorites: list[str] | None = None,
        **kwargs,
    ) -> list[str]:
        favorite_context = (
            mock.patch.object(
                naibbe_habit,
                "_choose_favorite_table",
                side_effect=favorites,
            )
            if favorites is not None
            else nullcontext()
        )
        with (
            mock.patch.object(
                naibbe_habit, "_new_deck", return_value=self.deck
            ),
            favorite_context,
        ):
            ciphertext, retries = naibbe_habit.encrypt_naibbe_habit(
                "".join(ngrams),
                self.tables,
                self.glyph_map,
                ngrams=ngrams,
                rng=random.Random(11),
                **kwargs,
            )
        self.assertEqual(retries, 0)
        self.assertEqual(len(ciphertext), len(ngrams))
        return ciphertext

    def test_favorite_table_is_scoped_to_one_bifolium(self) -> None:
        ciphertext = self.encrypt(
            list("abcdefgh"),
            favorites=["alpha", "beta1"],
            bifolia_per_quire=2,
            tokens_per_page=1,
            p_habit=1.0,
        )
        self.assertEqual(
            ciphertext,
            [
                "U[alpha:a]",
                "U[alpha:b]",
                "U[beta1:c]",
                "U[beta1:d]",
                "U[beta1:e]",
                "U[beta1:f]",
                "U[alpha:g]",
                "U[alpha:h]",
            ],
        )

    def test_habit_applies_one_favorite_table_across_a_bifolium(self) -> None:
        ciphertext = self.encrypt(
            ["a", "b", "c", "d"],
            favorites=["alpha"],
            bifolia_per_quire=1,
            tokens_per_page=1,
            p_habit=1.0,
        )
        self.assertEqual(len(set(ciphertext)), 4)
        self.assertTrue(all(token.startswith("U[alpha:") for token in ciphertext))

    def test_repeated_plaintext_is_encrypted_on_every_occurrence(self) -> None:
        generated = [
            (f"generated-{index}", self.deck, 0, 0)
            for index in range(4)
        ]
        with mock.patch.object(
            naibbe_habit,
            "_draw_token",
            side_effect=generated,
        ) as draw_token:
            ciphertext = self.encrypt(
                ["a", "a", "a", "a"],
                favorites=["alpha"],
                bifolia_per_quire=1,
                tokens_per_page=1,
                p_habit=1.0,
            )

        self.assertEqual(
            ciphertext,
            ["generated-0", "generated-1", "generated-2", "generated-3"],
        )
        self.assertEqual(draw_token.call_count, 4)

    def test_partial_final_quire_keeps_configured_physical_pairing(self) -> None:
        ciphertext = self.encrypt(
            ["a", "b", "c", "d"],
            favorites=["alpha", "beta1"],
            bifolia_per_quire=2,
            tokens_per_page=1,
            p_habit=1.0,
        )
        self.assertEqual(
            ciphertext,
            [
                "U[alpha:a]",
                "U[alpha:b]",
                "U[beta1:c]",
                "U[beta1:d]",
            ],
        )

    def test_deck_continues_across_quire_boundaries_without_habit(self) -> None:
        ciphertext = self.encrypt(
            list("abcdefgh"),
            bifolia_per_quire=1,
            tokens_per_page=1,
            p_habit=0.0,
        )
        self.assertEqual(
            ciphertext,
            [
                "U[alpha:a]",
                "U[beta1:b]",
                "U[beta2:c]",
                "U[beta3:d]",
                "U[gamma1:e]",
                "U[gamma2:f]",
                "U[alpha:g]",
                "U[beta1:h]",
            ],
        )

    def test_zero_habit_never_selects_a_favorite(self) -> None:
        with mock.patch.object(
            naibbe_habit, "_choose_favorite_table"
        ) as choose_favorite:
            self.encrypt(
                ["a", "b"],
                bifolia_per_quire=1,
                tokens_per_page=1,
                p_habit=0.0,
            )
        choose_favorite.assert_not_called()

    def test_ambiguous_habit_bigram_falls_back_to_deck(self) -> None:
        alpha_prefix = self.tables["alpha"][("prefix", "a")]
        alpha_suffix = self.tables["alpha"][("suffix", "b")]
        unigram = self.tables["gamma2"][("unigram", "z")]
        self.glyph_map[alpha_prefix] = "X"
        self.glyph_map[alpha_suffix] = "Y"
        self.glyph_map[unigram] = "XY"

        with (
            mock.patch.object(
                naibbe_habit, "_new_deck", return_value=self.deck
            ),
            mock.patch.object(
                naibbe_habit,
                "_choose_favorite_table",
                return_value="alpha",
            ),
        ):
            ciphertext, retries = naibbe_habit.encrypt_naibbe_habit(
                "ab",
                self.tables,
                self.glyph_map,
                bifolia_per_quire=1,
                tokens_per_page=1,
                p_habit=1.0,
                ngrams=["ab"],
                rng=random.Random(7),
            )

        self.assertEqual(retries, 1)
        self.assertEqual(ciphertext, ["X" + "S[beta1:b]"])

    def test_seed_controls_all_randomness_without_global_state(self) -> None:
        ngrams = list("abacabadabacaba")
        random.seed(12345)
        global_state = random.getstate()

        first, _ = naibbe_habit.encrypt_naibbe_habit(
            "".join(ngrams),
            naibbe_habit.naibbe_tables,
            naibbe_habit.placeholder_to_glyph,
            bifolia_per_quire=2,
            tokens_per_page=2,
            p_habit=0.35,
            ngrams=ngrams,
            rng=random.Random(99),
        )
        second, _ = naibbe_habit.encrypt_naibbe_habit(
            "".join(ngrams),
            naibbe_habit.naibbe_tables,
            naibbe_habit.placeholder_to_glyph,
            bifolia_per_quire=2,
            tokens_per_page=2,
            p_habit=0.35,
            ngrams=ngrams,
            rng=random.Random(99),
        )

        self.assertEqual(first, second)
        self.assertEqual(random.getstate(), global_state)

    def test_ciphertext_remains_exactly_decryptable(self) -> None:
        ngrams = ["ar", "m", "a", "vi", "rm", "u", "m", "qu", "e"]
        ciphertext, _ = naibbe_habit.encrypt_naibbe_habit(
            "".join(ngrams),
            naibbe_habit.naibbe_tables,
            naibbe_habit.placeholder_to_glyph,
            bifolia_per_quire=2,
            tokens_per_page=2,
            p_habit=1.0,
            ngrams=ngrams,
            rng=random.Random(17),
        )
        reverse_maps = decrypt_naibbe.build_reverse_mappings(
            naibbe_habit.naibbe_v2.glyph_df
        )
        decrypted = [
            decrypt_naibbe.decrypt_naibbe_token(token, *reverse_maps)
            for token in ciphertext
        ]
        self.assertEqual(decrypted, ngrams)

    def test_supplied_ngrams_must_match_plaintext(self) -> None:
        with self.assertRaises(ValueError):
            naibbe_habit.encrypt_naibbe_habit(
                "ab",
                self.tables,
                self.glyph_map,
                ngrams=["a", "c"],
            )

    def test_invalid_habit_probability_fails(self) -> None:
        with self.assertRaises(ValueError):
            naibbe_habit.encrypt_naibbe_habit(
                "a",
                self.tables,
                self.glyph_map,
                p_habit=1.1,
                ngrams=["a"],
            )


class CommandLineTests(unittest.TestCase):
    def test_parser_uses_habit_program_and_probability_names(self) -> None:
        parser = naibbe_habit.build_parser()
        args = parser.parse_args(["--p-habit", "0.25"])

        self.assertEqual(parser.prog, "naibbe-habit")
        self.assertEqual(args.p_habit, 0.25)
        self.assertEqual(args.bifolia_per_quire, 4)
        api_default = inspect.signature(
            naibbe_habit.encrypt_naibbe_habit
        ).parameters["bifolia_per_quire"].default
        self.assertEqual(api_default, 4)


if __name__ == "__main__":
    unittest.main()
