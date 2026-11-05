"""Trailing words that make an English field label name a credential."""

# "MySQL password", "HMAC secret", "OpenRouter API key": the qualifier names the
# system, the last words name the credential. Bare "key" is absent on purpose:
# "Public key" and "Primary key" are not secrets.
CREDENTIAL_LABEL_SUFFIXES = (
    "password",
    "passwd",
    "passphrase",
    "secret",
    "secret key",
    "token",
    "api key",
    "apikey",
    "access key",
    "private key",
)
