"""Credential shapes a vendor stamps with a fixed prefix, taken from gitleaks' rules.

The exporter's original six patterns let Stripe live keys, Google API keys,
Airtable tokens, an age secret key, JSON-escaped and base64 private keys and
`export NAME_KEY=value` lines reach context output from curated notes
(gitleaks 8.30.1 over the served index, 2026-11-06). Each regex below follows
the gitleaks rule named beside it; only prefixed shapes are kept, because a
bare hex or base64 run is as often a hash or an id as a secret.
"""

import re

VENDOR_TOKEN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # private-key, written inline with literal "\n" escapes (JSON) or on one line
    (
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "[REDACTED:private-key]",
    ),
    # a PEM block base64-encoded once more: "-----BEGIN" is "LS0tLS1CRUdJT"
    (re.compile(r"\bLS0tLS1CRUdJT[A-Za-z0-9+/=]{40,}"), "[REDACTED:private-key]"),
    # stripe-access-token
    (re.compile(r"\b(?:sk|rk)_(?:test|live|prod)_[A-Za-z0-9]{10,99}\b"), "[REDACTED:token]"),
    # gcp-api-key
    (re.compile(r"\bAIza[\w-]{35}(?![\w-])"), "[REDACTED:token]"),
    # sendgrid-api-token
    (re.compile(r"\bSG\.[A-Za-z0-9=_\-.]{66}"), "[REDACTED:token]"),
    # perplexity-api-key
    (re.compile(r"\bpplx-[A-Za-z0-9]{48}\b"), "[REDACTED:token]"),
    # airtable-personnal-access-token
    (re.compile(r"\bpat[A-Za-z0-9]{14}\.[a-f0-9]{64}\b"), "[REDACTED:token]"),
    # age-secret-key
    (re.compile(r"AGE-SECRET-KEY-1[QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7L]{58}"), "[REDACTED:secret]"),
    # jwt (header and payload both start with base64 '{"')
    (
        re.compile(r"\bey[A-Za-z0-9]{17,}\.ey[A-Za-z0-9/\\_-]{17,}\.[A-Za-z0-9/\\_-]{10,}={0,2}"),
        "[REDACTED:token]",
    ),
    # sourcegraph-access-token (prefixed form only)
    (re.compile(r"\bsgp_(?:[a-fA-F0-9]{16}_|local_)?[a-fA-F0-9]{40}\b"), "[REDACTED:token]"),
    # dropbox-short-lived-api-token
    (re.compile(r"\bsl\.[A-Za-z0-9\-=_]{135}"), "[REDACTED:token]"),
    # github-fine-grained-pat
    (re.compile(r"\bgithub_pat_\w{82}\b"), "[REDACTED:token]"),
    # gitlab-pat
    (re.compile(r"\bglpat-[\w-]{20}\b"), "[REDACTED:token]"),
    # npm-access-token
    (re.compile(r"\bnpm_[A-Za-z0-9]{36}\b"), "[REDACTED:token]"),
    # huggingface-access-token
    (re.compile(r"\bhf_[A-Za-z]{34}\b"), "[REDACTED:token]"),
    # digitalocean-pat / -access-token / -refresh-token
    (re.compile(r"\bdo[opr]_v1_[a-f0-9]{64}\b"), "[REDACTED:token]"),
    # shopify-access-token and siblings
    (re.compile(r"\bshp(?:at|ca|pa|ss)_[a-fA-F0-9]{32}\b"), "[REDACTED:token]"),
    # linear-api-key
    (re.compile(r"\blin_api_[A-Za-z0-9]{40}\b"), "[REDACTED:token]"),
    # pypi-upload-token
    (re.compile(r"\bpypi-AgEIcHlwaS5vcmc[\w-]{50,}"), "[REDACTED:token]"),
    # postman-api-token
    (re.compile(r"\bPMAK-[a-f0-9]{24}-[a-f0-9]{34}\b"), "[REDACTED:token]"),
    # telegram-bot-api-token
    (re.compile(r"\b[0-9]{5,16}:AA[A-Za-z0-9_-]{33}\b"), "[REDACTED:token]"),
    # an environment assignment whose name says what it holds, with a token-shaped
    # value (letters and digits): `STOP_KEY = "Escape"` is a key binding, not a key
    (
        re.compile(
            r"(\b[A-Z][A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD)[A-Z0-9_]*\s*=\s*)"
            r"[\"']?(?!\[REDACTED:)(?=[^\s\"'`]*\d)(?=[^\s\"'`]*[A-Za-z])[^\s\"'`]{8,}"
        ),
        r"\g<1>[REDACTED:secret]",
    ),
]
