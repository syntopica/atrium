# Remote-export adapter family — spike

Design snapshot: 2026-09-01. A spike, not a specification: it exists because
ChatGPT and Grok leave no local transcript, and every exporter built so far
assumes one. That assumption is hardening with each adapter that shares it;
this records the contract a remote source needs before the next local-file
refactor bakes the assumption into the shared capture path. Implementation
belongs to `~/p/rocket-agents`; this copy keeps the reasoning where the
backlog item lives (precedent: `conversation-archive-v2.md`).

## The gap

Nothing has ever been captured from ChatGPT or Grok. They are the answer to
"is the archive complete" that no exporter fix can close: the data is not on
this machine. Both, however, ship an official account data export:

- **ChatGPT**: Settings -> Data Controls -> Export. OpenAI emails a download
  link (expires in 24 h) to a ZIP holding `conversations.json` (full history,
  tree-shaped `mapping` per conversation, timestamps and ids) plus
  `chat.html`.
- **Grok**: `accounts.x.ai/data` serves a ZIP with JSON for the whole
  account. No native per-chat export exists on grok.com or x.com/i/grok as of
  mid-2026.

Neither vendor offers a consumer API for conversation history. Browser
automation could scrape both, but a scraper is a second implementation of the
vendor's own export with strictly worse failure modes; the family starts from
the official archives.

## The shape: an inbox, not a watcher

Local exporters read live provider state; a remote source cannot be read, only
delivered to. The family therefore adds one concept to capture:

    ~/.local/share/rocket-agents/remote-inbox/<source>/

The operator (or a later automation) drops the vendor ZIP there, untouched.
The adapter's job is exactly what local exporters do after their read:
identify conversations, normalize to the canonical event schema, and hand them
to the same redaction and manifest machinery. Every path after the parse is
shared; only acquisition differs.

Contract per adapter:

1. **Input**: one vendor archive file, content-addressed on arrival (sha256);
   re-dropping the same ZIP is a no-op by hash, not by filename.
2. **Parse**: vendor-specific. ChatGPT's `mapping` tree is linearized by
   following `current_node` parents, the same way its own UI renders one
   branch; abandoned branches are kept as events of the same conversation
   rather than dropped (the archive holds everything, the index decides what
   earns a row).
3. **Redact THEN archive** — the same redaction pass local captures get, and
   the same hard boundary: raw vendor archives never leave the inbox
   directory, and the inbox is never read by anything but the adapter (the
   redaction-bypass rule that put 14 private-key blocks into the previous
   index applies here verbatim).
4. **Manifest honesty**: a remote export is complete only as of its request
   time. The manifest records `exportedAt` from the vendor archive's own
   metadata and declares `complete:false` with the staleness window, exactly
   as the codex export declares its two oversized skips. "The archive is
   complete except that ChatGPT is 40 days stale" must be a queryable fact,
   not a memory.
5. **Provenance**: `source: chatgpt` / `source: grok`, conversation ids as
   the vendor assigns them, `provenance.contentSha256` over the normalized
   conversation as usual, plus the inbox archive's hash so a record can be
   traced to the exact ZIP it came from.

## Cadence, and why staleness is acceptable

The exports are manual (an email round-trip for ChatGPT, a portal visit for
Grok). That caps freshness at how often the operator bothers -- realistically
monthly. The alternative lanes, in order of preference if that becomes
unacceptable:

- vendor adds an API or scheduled export (watch for it, cost zero);
- a browser-automation requester that only *triggers* the official export and
  downloads the emailed ZIP into the inbox -- automation of acquisition, never
  of parsing live DOM;
- full scraping. Last, because it re-implements the export against an
  unversioned UI and breaks silently -- the exact failure class the archive
  exists to prevent.

`atrium doctor` already reports archive staleness globally; a per-source
`exportedAt` in the manifest lets it name the stale remote source directly.

## What this spike deliberately does not decide

- Whether ChatGPT "projects"/custom-GPT threads need distinct workspace
  mapping (needs a real export in hand).
- Grok's exact JSON shape (undocumented; first real ZIP decides the parser).
- Whether inbox drops should be synced between machines or each machine
  imports its own (leaning: inbox is machine-local scratch, the archive is
  the sync surface, same as today).

Smallest next step: request both exports, drop them in the inbox layout, and
write the ChatGPT parser against the real `conversations.json` -- its format
is documented well enough that the parser is a day, not a design.

Sources: [ChatGPT export mechanics](https://saveai.net/blog/how-to-export-chatgpt-conversations),
[conversations.json structure](https://www.chatgptexporter.com/en/blog/how-to-export-chatgpt-to-json),
[Grok/xAI data download](https://www.ai-toolbox.co/grok-management-and-productivity/how-to-back-up-grok-conversations-2026),
[Grok export state](https://chatexport.guide/guides/grok/).
