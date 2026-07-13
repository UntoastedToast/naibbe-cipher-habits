# The Naibbe Cipher: Bifolium-Based Scribal Habit Extension

> **Note:** This repository is a fork of Michael A. Greshko's original Naibbe cipher implementation. It extends the codebase with a bifolium-based scribal habit model (`naibbe_habit.py`).
>
> This implementation was created in the context of the digital humanities exercise "Das Voynich Manuskript als Forschungsobjekt" at the IDH (Institut für Digital Humanities), University of Cologne.

## Project Description

While the original Naibbe cipher successfully encrypts Latin and Italian texts into Voynich-like ciphertext, this fork investigates how a local scribal habit tied to bifolia affects the statistical properties of the resulting text. The experiment takes up the proposal for future research in Greshko (2025), section 4.2, and asks whether bifolium-based working units can contribute to long-range correlations in reading order.

This project is an educational exploration within the Digital Humanities, building upon the theoretical foundations laid by Greshko's work.

## Scope of the habit model

Section 4.2 first reports a limitation of the published Naibbe cipher: its
random respacing and card draws do **not** reproduce the VMS's observed
long-range correlations. Greshko then proposes a mechanism for future study. If
a scribe encrypted one bifolium at a time and made non-random local choices,
the four affected pages would be separated after folding and binding. A habit
that was local during production could consequently appear at long distances
in reading order.

`naibbe_habit.py` implements one explicit, decryptable operationalization of
that proposal:

1. The plaintext is respaced once with the standard Naibbe rule and assigned
   to pages in final reading order.
2. Nested bifolia are processed from outermost to innermost. Each bifolium owns
   two pages near the front and two mirrored pages near the back of its quire.
3. At the beginning of each non-empty bifolium, one substitution table is
   selected as the scribe's local favourite. The selection follows the normal
   Naibbe table weights.
4. For each table choice, the favourite is used with probability `p_habit`.
   Otherwise, encryption continues with the normal Naibbe card deck.
5. The selected table is applied through the standard Naibbe substitution
   procedure. A new favourite is selected for the next bifolium before the
   pages are restored to reading order.

The no-habit control uses `p_habit=0`; `p_habit=1` is the maximal version of
the model. Because favourites and ordinary card draws use the same base
weights, the parameter changes local clustering without intentionally changing
the global table proportions. If a bigram would be ambiguous, its retry uses
the ordinary deck rather than the habit.

This implementation operationalizes Greshko's research direction with
`p_habit=0.5` and 160 tokens per page as experimental parameters. The default
quire size of four bifolia follows the standard codicological description of
the Voynich Manuscript: four bifolia form eight folios or sixteen written pages.
The manuscript also contains exceptional gatherings, missing leaves, and
foldouts, which this deliberately simple model does not reproduce. See Zyats
et al. (2016, pp. 23-37) and the detailed
[collation description](https://www.voynich.nu/descr.html).

The implementation uses one seeded random-number generator for respacing,
card shuffles, and sensitivity runs, and keeps the Naibbe deck continuous until
it is exhausted. A partially filled final quire retains its configured physical
page pairing instead of being silently resized.

```bash
python naibbe_habit.py --seed 42 --p-habit 0.5
python -m unittest discover -s tests -v
```

The paper-compatible 100-text results and their limitations are documented in
[`RESULTS.md`](RESULTS.md).

## Paper-compatible 42-metric evaluation

`naibbe_habit_evaluate.py` compares the habit model with the 20 published Naibbe
reference ciphertexts using the same 42 linguistic metrics that Greshko used.
The experiment uses the exact four normalized 8,000-letter excerpts from the
paper supplement, stored separately under
`figure_utils/habit_evaluation/data/`. Original spaces and punctuation are
absent because Naibbe performs its own random unigram/bigram respacing.

The historical Gaskell/Bowern program remains unchanged as
`figure_utils/gaskell_bowern_2022/stats.py`. The experiment calls the separate
`stats_habit.py` derivative, whose header documents every technical change:
deterministic subset sampling and explicit, portable output paths. The 42
metric definitions are unchanged.

The default matrix consists of ten seeds, both Naibbe decks, and
`p_habit = 0, 0.3, 0.5, 1`, giving 80 paired habit runs plus the 20 published
references. The z-score calibration is frozen to the existing 952-document
corpus so adding habit texts cannot move the benchmark.

```bash
uv sync --extra eval
uv run --extra eval naibbe-habit-evaluate
```

The command writes per-run metrics, group summaries, paired metric deltas, and
the Hurst-versus-distance plots to `figure_utils/habit_evaluation/results/`.
Use `--help` to select fewer seeds or subset iterations for a smoke test.

---

## Original Work: The Naibbe Cipher

This project builds entirely on the work of Michael A. Greshko. The original repository contains the foundational code and datasets associated with the following paper:

> Greshko, Michael A. (2025). The Naibbe cipher: a substitution cipher that encrypts
Latin and Italian as Voynich Manuscript-like ciphertext.
Cryptologia. https://doi.org/10.1080/01611194.2025.2566408
  
### Original Abstract

In the work represented here and in the associated study, I investigate
the hypothesis that the Voynich Manuscript (MS 408, Yale University Beinecke
Library) is compatible with being a ciphertext by attempting to develop a
historically plausible cipher that can replicate the manuscript’s unusual
properties. The resulting cipher—a verbose homophonic substitution cipher I call
the Naibbe cipher—can be done entirely by hand with 15th-century materials, and
when it encrypts a wide range of Latin and Italian plaintexts, the resulting
ciphertexts remain fully decipherable and also reliably reproduce many key
statistical properties of the Voynich Manuscript at once. My results suggest
that the so-called “ciphertext hypothesis” for the Voynich Manuscript remains
viable, while also placing constraints on plausible substitution cipher
structures.

### Original Data and extended output

Additional datasets, including the original Microsoft Excel implementations of
the Naibbe cipher and Voynichesque, can be found at:
https://doi.org/10.5281/zenodo.16415087

Extensive discussion of a preprint version of this paper can be accessed at:
https://www.voynich.ninja//thread-4848.html

# License and copyright

Unless otherwise indicated, the source code contained in
this repository is provided under the modified MIT license below.

---

Copyright (c) 2025, Michael A. Greshko.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software, datasets, and associated documentation files (the "Software
and Datasets"), to deal in the Software and Datasets without restriction,
including without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software and Datasets, and to
permit persons to whom the Software is furnished to do so, subject to the
following conditions:

- The above copyright notice and this permission notice shall be included
  in all copies or substantial portions of the Software and Datasets.
- Any publications making use of the Software and Datasets, or any substantial
  portions thereof, shall cite the Software and Datasets's original publication:

> Greshko, Michael A. (2025). The Naibbe cipher: a substitution cipher that encrypts
Latin and Italian as Voynich Manuscript-like ciphertext.
Cryptologia. https://doi.org/10.1080/01611194.2025.2566408
  
THE SOFTWARE AND DATASETS ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE AND DATASETS.
