"""Choose the curated page a claim belongs to, or refuse to place it."""

from atrium.curate.destination_tool import NO_DESTINATION, destination_tool
from atrium.curate.page_descriptor import page_descriptor
from atrium.curate.page_library import PageLibrary
from atrium.curate.page_shortlist import page_shortlist
from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL, local_lane_call

_SYSTEM = (
    "You place one fact from an engineering session into a personal knowledge wiki. "
    "Each candidate page is given as its path, its title and its one-line summary. "
    "Pick the page where a reader looking for this fact later would expect to find it. "
    "Answer NONE when the fact belongs to no candidate: a file-level code detail that "
    "only mattered inside one pull request has no page, and inventing a home for it is "
    "worse than dropping it."
)
_INSTRUCTION = "Now choose ONE destination as a JSON object matching this schema."
_SHORTLIST = 5


def claim_destination(
    library: PageLibrary,
    claim: str,
    project_page: str | None = None,
    model: str = LOCAL_DEFAULT_MODEL,
) -> tuple[str | None, str, list[str]]:
    """Return the chosen page (``None`` for no home), the reason, and the shortlist.

    The claim's own project page is appended to the shortlist when it exists and
    retrieval missed it, because the deterministic workspace join knows one thing
    retrieval cannot: which repository the session was actually in. Measured on
    40 durable claims with both offered, the model took a retrieved page 21
    times, the project page 5, and refused 14 - so the join is a useful
    candidate and a poor default.
    """
    shortlist = [hit.path for hit in page_shortlist(library, claim, _SHORTLIST)]
    if project_page and project_page not in shortlist and (library.root / project_page).is_file():
        shortlist.append(project_page)
    if not shortlist:
        return None, "no candidate page", []
    listing = "\n".join(f"- {path}: {page_descriptor(library.root, path)}" for path in shortlist)
    answer = local_lane_call(
        LanePrompt(_SYSTEM, f"FACT:\n{claim}\n\nCANDIDATE PAGES:\n{listing}", _INSTRUCTION, "FACT"),
        destination_tool(shortlist),
        model=model,
    )
    chosen = str(answer["input"]["destination"])
    why = str(answer["input"]["why"])
    return (None if chosen == NO_DESTINATION else chosen), why, shortlist
