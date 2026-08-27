"""Bilingual stopwords for the episode cutter's TF-IDF, pinned.

Part of the `episode-texttiling-v1` fingerprint: changing this set changes
episode boundaries, so it changes the segmentation version, never silently.
"""

SPANISH_ENGLISH_STOPWORDS = frozenset(
    """
a al algo como con cual cuando de del desde donde el ella ellas ellos en entre
era eran es esa ese eso esta este esto fue ha han hasta hay la las le les lo
los mas me mi mis muy no nos o os otra otro para pero por que se ser si sin
sobre son su sus te tu tus un una uno unos ya yo
the a an and or but if then else when at by for with about against between
into through during before after above below to from up down in out on off
over under again further once here there all any both each few more most
other some such no nor not only own same so than too very can will just do
does did doing done is are was were be been being have has had having i you
he she it we they them his her its our their this that these those what which
who whom
""".split()  # noqa: SIM905 -- a word-per-line block reads as the wordlist it is
)
