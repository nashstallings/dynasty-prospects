"""Name normalization shared between prospect_id construction and dashboard joins.

The fact tables have no stable prospect_id of their own (only dim_prospect does),
so anything that needs to line a fact row up with a prospect matches on this
normalized name instead. Keeping it in one place means the join can't drift
from how prospect_id itself was built.
"""

import re

_NON_LETTERS = re.compile(r"[^a-z ]")


def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return _NON_LETTERS.sub("", name.lower()).replace(" ", "_")
