"""Pure text helpers shared by the ingestion routes.

Kept free of heavy imports (no LLM clients, no storage singletons) so it can be
imported and unit-tested without standing up the whole app.
"""
import re

# A run of at least 5 single letters separated by single spaces/tabs.
#
# The \b anchors matter: without them the run starts mid-word and eats the
# previous word's final letter ("the V a l v e" -> "theValve"), and ends by
# absorbing the first letter of the next word. Staying off \n also stops a run
# from gluing two lines together.
_SPACED_OUT_PATTERN = re.compile(r'\b(?:[A-Za-z][ \t]){4,}[A-Za-z]\b')


def clean_spaced_text(text: str) -> str:
    """
    Detects and fixes 'spaced-out' text (e.g. 'C o n t a i n e r i z a t i o n')
    which is a common artifact in certain PDF extractions.

    Surrounding words and their spacing are left intact.
    """
    if not text:
        return text

    def replacer(match):
        # Collapse the artifact itself; the boundaries around it are untouched.
        return match.group(0).replace(" ", "").replace("\t", "")

    return _SPACED_OUT_PATTERN.sub(replacer, text)
