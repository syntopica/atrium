"""The word pattern episode segmentation counts and compares."""

import re

# Part of the `episode-texttiling-v1` fingerprint: two or more letters or digits.
EPISODE_WORD = re.compile(r"[^\W_]{2,}", re.UNICODE)
