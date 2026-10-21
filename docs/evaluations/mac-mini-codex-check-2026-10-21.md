# Mac mini Codex memory check — 2026-10-21

## Verified state

Both Atrium checkouts and the mini's installed CLI release were at `e582eb6`.
The mini had an enabled Atrium MCP registration, but no Atrium plugin or legacy
Atrium hook registrations. Repository synchronization had not installed the
Codex plugin.

Installed the local marketplace and `atrium-context@atrium`, preserved a private
configuration backup, and recorded trust for its six reviewed hook definitions
using Codex's native `config/batchWrite` interface. No unrelated hooks changed.
The installed package matched all ten source files byte for byte.

Verification used a fresh `codex app-server --stdio` process: `initialize`,
then `hooks/list` with `cwds` selecting this repository. It reported exactly six
Atrium hooks, all enabled and trusted, with no loading errors. This verifies
runtime discovery; it does not claim an existing Codex session reloaded.

Executing the installed SessionStart handler with the repository as `cwd`
recalled 12 episodes and produced 1,699 characters of additional context.
Executing the installed UserPromptSubmit handler with the same scope produced
1,501 characters of context without the unavailable notice.

## Retrieval and synchronization limits

The first live context query returned `context_service_timeout` after 7,009 ms.
A later identical query returned eight evidence records, `index_status=ready`,
and `served_by=service` after 5,295 ms. Warnings included
`rerank_unavailable_fused_order`, unresolved or unsafe links, and a reached
candidate limit. This is usable retrieval with observed degraded behavior,
not evidence of consistently healthy latency.

The mini's published refresh report showed 461,901 indexed records and a refresh
at 06:09:40 UTC. Freshness does not establish archive parity. No full archive
comparison, index rebuild, embedding run, or benchmark was started. The index
must remain machine-local. The laptop's uncommitted comparison harness and
private experiment artifacts were not copied to the mini.

## Recheck commands

```sh
codex plugin list --json
atrium context "What decisions govern canonical archive and disposable index?" --project ~/p/atrium --json
```

Review the six handlers with `/hooks` in a newly opened Codex session. Updating
the checkout alone does not update the cached plugin: rerun `codex plugin add
atrium-context@atrium --json` after a package change, review changed hooks, and
verify discovery again.
