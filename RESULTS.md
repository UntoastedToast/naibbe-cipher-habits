# Ergebnisse des bifoliumbasierten Habit-Modells

**Stand** 12. Juli 2026

**Status** Explorative Auswertung mit einem Klartext und einem Seed

Dieser Bericht untersucht eine offene Frage aus Abschnitt 4.2 von Greshkos
Aufsatz. Können lokale Entscheidungen beim Verschlüsseln eines Bifoliums dazu
führen, dass im gebundenen Codex Zusammenhänge über größere Textabstände
sichtbar werden?

Das Experiment verbindet die materielle Ordnung des Codex mit einem einfachen
Modell für eine Schreibgewohnheit. Eine Lage besteht aus mehreren gefalteten
Doppelblättern oder Bifolia. Was bei der Arbeit auf einem Bifolium unmittelbar
zusammengehörte, kann nach dem Falten und Binden auf weit voneinander
entfernten Seiten stehen. Diese Beziehung bildet das Programm nach.

## Ausgangspunkt

Der ursprüngliche Naibbe-Cipher erzeugt viele Eigenschaften, die an das
Voynich-Manuskript erinnern. Die langreichweitigen Korrelationen von Voynich B
werden nach Greshko jedoch nicht erreicht. Er nennt deshalb die Arbeit auf
einzelnen Bifolia als möglichen Ansatz für weitere Versuche. Das Habit-Modell
macht diese Forschungsrichtung als rechnerisches Experiment prüfbar.

Das Habit-Modell übersetzt diesen Vorschlag in eine lokale Bevorzugung bei der
Wahl der Substitutionstabelle. Der Eingriff bleibt damit auf eine
Entscheidungsebene beschränkt, die bereits zum Kartensystem des Naibbe-Ciphers
gehört.

## Das Habit-Modell

Der Klartext wird zunächst nach dem Naibbe-Verfahren in Gruppen aus einem oder
zwei Buchstaben zerlegt. Jeweils 160 Gruppen werden einer Seite zugeordnet.
Vier Seiten gehören zu einem Bifolium. Das Programm bearbeitet die Bifolia von
außen nach innen und stellt die Seiten anschließend wieder in Lesereihenfolge
zusammen.

Für die Größe einer Lage setzt das Experiment vier Bifolia an. Eine solche
Standardlage umfasst acht Folia und damit sechzehn beschriebene Seiten. Diese
Entscheidung folgt der kodikologischen Beschreibung des Voynich-Manuskripts
(Zyats et al. 2016, 23-37; Zandbergen o. J.). Die Handschrift enthält daneben
abweichende Lagen, fehlende Blätter und komplexe Ausfaltblätter. Sie werden hier
nicht nachgebildet, weil allein der Einfluss von `p_habit` untersucht werden
soll.

Für jedes nicht leere Bifolium wird eine bevorzugte Naibbe-Tabelle gezogen.
Wir nennen sie die Favoritentabelle. Ihre Auswahl folgt denselben Gewichten wie
der normale Kartenstapel. Bei jeder Tabellenwahl entscheidet `p_habit`, ob die
Favoritentabelle oder die nächste Karte des Stapels verwendet wird. Der Stapel
läuft über Seiten- und Lagengrenzen hinweg weiter.

Bei `p_habit = 0` gibt es keine lokale Bevorzugung. Der Wert `1` bezeichnet die
stärkste Variante. Dann wird zunächst immer die Favoritentabelle verwendet.
Nur wenn ein Zweier-Token mehrdeutig wäre, greift der erneute Versuch auf den
normalen Stapel zurück. So bleibt der Chiffretext eindeutig entschlüsselbar.

Die Favoritentabelle bildet die gemeinsame lokale Gewohnheit eines Bifoliums.
Da sie und der Kartenstapel denselben Grundgewichten folgen, sollen sich die
globalen Tabellenanteile im Erwartungswert nicht verschieben. Der Parameter
bündelt die Auswahl vielmehr zeitlich und räumlich.

Dieses Modell ist eine bewusst einfache Operationalisierung. `p_habit`, die
Seitenlänge und die Bearbeitungsreihenfolge der Bifolia bilden die festen
Versuchsannahmen. Die Größe von vier Bifolia ist eine kodikologisch begründete
Modellkonstante.

## Material und Vergleich

Als Klartext dient die lateinische Fassung von Plinius' *Naturalis historia*,
Buch 16
([`input/examples/nathist_book16.txt`](input/examples/nathist_book16.txt)). Die
Referenz ist die
[Currier-B-Transkription](<figure_utils/gaskell_bowern_2022/data/voynichese/Voynichese - Currier B - EVA Basic.txt>)
in EVA Basic. Alle hier berichteten Naibbe-Läufe verwenden den Seed `42` und
den Stapel mit 78 Karten.

Der Vanilla-Lauf führt `naibbe_v2.py` in seiner ursprünglichen zeilenweisen
Form aus. Die Habit-Kontrolle nutzt bereits die neue Ganztext- und
Bifolium-Pipeline, setzt aber `p_habit = 0`. Sie ist der wichtigere Vergleich
für die Habit-Varianten, weil sich innerhalb dieser Gruppe nur die lokale
Tabellenbevorzugung ändert. Die leicht abweichende Tokenzahl von Vanilla
entsteht durch die Behandlung der Zeilengrenzen bei der Neuaufteilung des
Klartexts.

## Messung

Für die RMSF-Auswertung wird jeder Chiffretext in eine binäre Folge übersetzt.
Aus dieser Folge entsteht ein eindimensionaler Zufallsweg. Wir messen seine
mittlere Schwankung für 20 Fenstergrößen zwischen ungefähr 20 und 50.000 Bits.
Höchstens 500.000 Bits eines Textes gehen in die Rechnung ein.

Die Steigung der RMSF-Kurve wird als Hurst-Wert `H` zusammengefasst. Ein Wert
um `0,5` steht in dieser Auswertung für einen Verlauf ohne deutliche
langreichweitige Persistenz. Höhere Werte zeigen stärkere Abhängigkeiten über
größere Skalen. Mit demselben Verfahren liegt Voynich B bei `H = 0,677`.

Ergänzend berechnen wir die kumulative Autokorrelation bis zu einem Abstand von
1.000 Bits. Hinzu kommen die Zahl der Token und Typen, die Type-Token-Ratio,
die mittlere Tokenlänge sowie zwei Entropiemaße. Der ausgegebene
Crossover-Punkt reagiert empfindlich auf kleine Änderungen. Wir behandeln ihn
daher nicht als eigenständigen Befund.

## Ergebnisse

| Konfiguration | `p_habit` | Token | Typen | TTR | Hurst `H` |
|---|---|---|---|---|---|
| Vanilla | - | 34.756 | 5.785 | 0,166 | 0,455 |
| Habit-Kontrolle | 0,0 | 34.487 | 5.808 | 0,168 | 0,493 |
| Schwache Bevorzugung | 0,3 | 34.487 | 5.797 | 0,168 | 0,567 |
| Mittlere Bevorzugung | 0,5 | 34.487 | 5.587 | 0,162 | 0,662 |
| Durchgängige Bevorzugung | 1,0 | 34.487 | 2.439 | 0,071 | 0,688 |
| Voynich B | - | 23.297 | 5.468 | 0,235 | 0,677 |

Die Habit-Kontrolle liegt mit `0,493` über dem Vanilla-Wert von `0,455`. Der
Abstand beträgt `0,038`. Bei nur einem Seed lässt sich daraus noch kein stabiler
Effekt der bifoliumweisen Bearbeitung ableiten. Die schwache Bevorzugung hebt
den Hurst-Wert deutlicher auf `0,567` an.

Bei `p_habit = 0,5` steigt `H` auf `0,662`. Der Abstand zu Voynich B beträgt
damit nur noch `0,015`. Die durchgängige Bevorzugung überschreitet die Referenz
mit `0,688` leicht. Ihr absoluter Abstand von `0,011` ist in diesem Lauf am
kleinsten.

Die kumulative Autokorrelation bis 1.000 Bits trennt die Varianten nur schwach.
Der sichtbare Unterschied stammt vor allem aus der RMSF-Kurve über größere
Fenster. Der Hurst-Wert sollte deshalb nicht für sich allein als Nachweis einer
bestimmten Textgenese gelesen werden.

## Vielfalt und Entropie

Die mittlere Variante bewahrt die Typenvielfalt vergleichsweise gut. Gegenüber
der Habit-Kontrolle sinkt die Zahl der Typen bei `p_habit = 0,5` von 5.808 auf
5.587. Das entspricht einem Rückgang von knapp vier Prozent. Die TTR liegt mit
`0,162` nahe am Vanilla-Wert von `0,166`.

Bei durchgängiger Bevorzugung sieht das anders aus. Nur noch 2.439 Typen kommen
vor. Gegenüber der Kontrolle fehlen rund 58 Prozent. Der Hurst-Wert liegt
damit zwar nahe an Voynich B, doch der Chiffretext wird in einer anderen
Hinsicht deutlich ärmer. Diese Variante erscheint deshalb nicht als die
überzeugendste Einstellung.

| Konfiguration | Zeichenentropie | Bedingte Zeichenentropie | Mittlere Tokenlänge |
|---|---|---|---|
| Habit-Kontrolle | 3,856 | 2,500 | 4,827 |
| Mittlere Bevorzugung | 3,858 | 2,494 | 4,821 |
| Durchgängige Bevorzugung | 3,861 | 2,488 | 4,811 |
| Voynich B | 3,968 | 2,429 | 4,822 |

Die mittlere Tokenlänge verändert sich kaum. Auch die Zeichenentropie bleibt
über die Naibbe-Varianten hinweg recht stabil. Am stärksten reagiert die Zahl
der unterschiedlichen Token. Die TTR von Voynich B lässt sich allerdings nur
eingeschränkt direkt vergleichen, weil der Referenztext kürzer ist und die TTR
von der Korpusgröße abhängt.

## Einordnung

Der Versuch stützt zunächst eine begrenzte Aussage. Eine lokale Gewohnheit bei
der Tabellenwahl kann in dieser Implementierung die gemessenen
langreichweitigen Korrelationen erhöhen. Der stärkste Anstieg gegenüber der
Kontrolle tritt erst bei mittlerer und durchgängiger Tabellenbevorzugung auf.

Als ausgewogenste der getesteten Einstellungen erscheint `p_habit = 0,5`.
Sie nähert den Hurst-Wert deutlich an Voynich B an, ohne die Typenvielfalt so
stark zu verringern wie die maximale Variante. Das ist jedoch eine Bewertung
innerhalb dieses Experiments und keine historisch belegte Parameterwahl.

Von einer Bestätigung der Hypothese kann noch nicht gesprochen werden. Wir
haben nur einen lateinischen Klartext und einen Seed untersucht. Der
Zusammenhang könnte bei anderen Zufallsfolgen oder Texten schwächer ausfallen.
Zudem hängt der Hurst-Wert von der verwendeten Transkription, der Binärkodierung,
den Fenstergrößen und dem Fitbereich ab.

Der Nutzen des Modells liegt daher weniger in
einem einzelnen möglichst ähnlichen Kennwert. Es macht vielmehr prüfbar,
welche statistischen Folgen eine konkrete Annahme über den Schreibprozess hat.
Eine solche Simulation kann historische Plausibilität nicht ersetzen. Sie
kann aber zeigen, welche Annahmen mit den beobachteten Daten vereinbar wären
und an welchen Stellen neue Probleme entstehen.

## Nächste Schritte

Für eine belastbarere Auswertung brauchen wir mehrere Seeds sowie weitere
lateinische und italienische Klartexte. Dann lassen sich Mittelwerte,
Streuungen und Unsicherheitsintervalle angeben. So ließe sich prüfen, wie stabil
der beobachtete Zusammenhang zwischen `p_habit` und dem Hurst-Wert ist.

Die Seitenlängen und die Lagenstruktur könnten sich später enger am
Voynich-Manuskript orientieren. Dazu gehören unterschiedlich lange Seiten,
unregelmäßige Lagen und fehlende Blätter. Neben RMSF und Hurst sollten auch
Wortgrammatik, positionsabhängige Glyphenverteilungen und Wiederholungsmuster
gemeinsam bewertet werden.

## Reproduzierbarkeit

Code, Tabellen und Abbildungen sind gemeinsam versioniert. Die Tests prüfen
unter anderem die Bifoliumzuordnung, den Kontrollfall ohne Habit, den Umgang
mit mehrdeutigen Zweier-Token, die Seed-Reproduzierbarkeit und die vollständige
Entschlüsselbarkeit.

```bash
uv sync --extra eval
python -m unittest discover -s tests -v
jupyter nbconvert --to notebook --execute naibbe_experiment.ipynb \
  --output naibbe_experiment_executed.ipynb \
  --output-dir /tmp \
  --ExecutePreprocessor.timeout=600
```

Das Notebook schreibt die Tabellen und Abbildungen an ihre versionierten
Zielorte im Repository.

## Dateien

- [Hurst- und Crossover-Werte](figure_utils/rmsf/ssc_hurst_comparison.csv)
- [Token-, Typen- und Entropiemetriken](figure_utils/rmsf/ssc_metrics_comparison.csv)
- [RMSF-Vergleich mit Voynich B](figure_utils/rmsf/long_range_plots/ssc_vs_voynich_b_overlay.png)
- [Kumulative Autokorrelation](figure_utils/rmsf/long_range_plots/ssc_autocorrelation_comparison.png)
- [Ausführbares Experiment](naibbe_experiment.ipynb)

## Literatur

Greshko, Michael A. 2025. "The Naibbe cipher: a substitution cipher that
encrypts Latin and Italian as Voynich Manuscript-like ciphertext."
*Cryptologia*. <https://doi.org/10.1080/01611194.2025.2566408>.

Zandbergen, René. o. J. "Description of the Voynich MS." Zugriff am 12. Juli
2026. <https://www.voynich.nu/descr.html>.

Zyats, Paula, Erin Mysak, Jens Stenger, Marie-France Lemay, Anikó Bezur und
David D. Driscoll. 2016. "Physical Findings." In *The Voynich Manuscript*,
herausgegeben von Raymond Clemens, 23-37. New Haven: Yale University Press.
