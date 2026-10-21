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

## Full configuration follow-up

Compared fresh native `skills/list` and `hooks/list` responses on both hosts,
using Codex CLI 0.163.0 and forcing skill rediscovery. Neither host reported
skill parsing errors, hook loading errors, or broken links in either user skill
root. The earlier filesystem count of five mini skills was incomplete: it did
not cover the shared skill root and installed plugin skills.

The laptop discovered 347 skill entries and the mini 351. All 336 shared library
manifests matched by SHA-256. Twenty-three had different enablement: enabled on
the mini, disabled on the laptop. Matched these settings through native
`skills/config/write`, preserving every skill file and backing up configuration.
A new process then reported no enablement differences across 341 common paths.
The resulting enabled counts were 49 on the laptop and 53 on the mini.

Remaining skill differences belong to host-managed OpenAI packages. The laptop
has Computer History; the mini has browser, Chrome, computer-use and the older
two-part Sites package. Five document, PDF, presentation and spreadsheet skill
bodies differ with their installed runtime versions. These packages were not
copied between application runtimes.

The mini lacked three BRP Codex registrations despite having identical copies
of all nine hook resources. Added only the SessionStart reminder, prompt skill
router and Stop verification handler, backed up the existing configuration,
and recorded trust with native `config/batchWrite`. Fresh `hooks/list` now
reports 28 enabled, trusted handlers on each host. Existing Orca, collector,
Warp and Atrium handlers remain present. Direct installed-handler checks passed:
the reminder injected its protocol, a release prompt selected `brp-release`,
and Stop with no edited transcript exited silently. This does not establish
the Stop handler's behavior on a real edited Codex transcript.

On the mini, `guidance:sync --accept-published` took the deterministic adoption
path, without a reconciliation agent or semantic rewrite, and preserved a
snapshot. `guidance:doctor` then returned `ok=true` with no findings. A fresh
native `thread/start` selected both the global and project `AGENTS.md`, as
reported in `instructionSources`; the test was ephemeral, disabled MCP startup
for that thread, and started no inference turn.

The canonical shared and Codex overlay sources match across hosts. The laptop
still has two locally shortened inventory/discovery passages and five accepted
guidance hash drifts reported by its doctor. Those live-only edits were not
overwritten. Follow-up convergence findings are recorded in the control plane's
own backlog, including the risk of generated skill trim undoing current parity.

Finally, launched the exact Atrium MCP command from the mini's user configuration,
completed `initialize` and `tools/list` (four tools), and called `atrium_context`.
It returned two evidence records, `index_status=ready`, `served_by=service`,
and `isError=false` in 4,864 ms. Rerank, unresolved-link and candidate-limit
warnings remained visible. The test's process group was terminated afterward.

Verification interfaces and commands for this follow-up were `hooks/list`,
`skills/list` with `forceReload=true`, `thread/start`, MCP `tools/call`, and:

```sh
cd ~/p/agents
pnpm run guidance:doctor -- --config ~/p/dotfiles/agent-guidance --json
```
