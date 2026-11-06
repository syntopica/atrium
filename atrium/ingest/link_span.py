"""The extent of a markdown or wiki link, which a positional cut must not split."""

import re

# A wikilink with the in-page target some pages give it (`[[S1]](#sources)`),
# or a markdown link with its target. Bounded per line, like the readers.
LINK_SPAN = re.compile(r"\[\[[^\]\n]+\]\](?:\([^)\s]*\))?|\[[^\]\n]*\]\([^)\n]*\)")
