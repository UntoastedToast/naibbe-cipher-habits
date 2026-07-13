# Paper plaintext fixture

The four `*_8000.txt` files form the exact sampler used by Greshko's Naibbe
workbook. They were extracted from the `text dropdown` worksheet of
`Naibbe Cipher.xlsx` in the supplementary materials for Greshko (2025),
Zenodo DOI: <https://doi.org/10.5281/zenodo.16415087>.

The evaluation concatenates, without inserted separators:

1. `dante_8000.txt`: cell B2 (Dante),
2. `de_sphaera_8000.txt`: cell B14 (Grosseteste, *De sphaera*),
3. `alchemical_herbal_8000.txt`: cell B15 (Latin alchemical herbal),
4. `pliny_book16_8000.txt`: cell B16 (Pliny, Book 16).

Each fixture contains 8,000 normalized lowercase letters. Original word
boundaries, punctuation, and capitalization are intentionally absent because
Naibbe creates its own random unigram/bigram segmentation before encryption.
The SHA-256 digests of the letter content (excluding the final file newline)
are:

- Dante: `e3fdb47bf611b53d5478e433c13b4aa92e3713add8e149e90a7735bc15112c49`
- *De sphaera*: `05ade4d609df85afcfb1e7f3c00dc0fe1b700eb190f66f197fa6e47dc036dbfc`
- Herbal: `141c3cd47201bd341680df6ade8d04475fc848f84b010262fe1916b2d2d5ad7e`
- Pliny: `fef9a1dac4c4382bad1aa2284d749e3f225fb9c1cc251a1277fee7f490cb0cf1`

Their concatenated content has SHA-256
`e6f005cc3d1b5610006cb7241e9f9928671ab98e00db6ffbdf95de6e8be2bfe8`.

This fixed normalized fixture avoids source-edition, header, and cleanup
differences. The pre-respaced files elsewhere in the repository are not used:
each experiment seed creates one fresh tokenization, which is then shared by
the paired habit configurations.
