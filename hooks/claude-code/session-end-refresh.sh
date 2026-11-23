#!/bin/sh
# SessionEnd hook: ask the scheduler for a refresh now, so what was just
# discussed is retrievable in the next session rather than up to an hour later.
#
# Not a Stop hook: Stop fires after every assistant response. The hook starts
# nothing itself. It kicks the job `syntopica schedule` installed, which the
# scheduler never runs twice at once and whose own floor drops a run that
# follows another too closely, so no lock is needed. Always exits 0: a session
# must end whether or not a refresh could be requested.
cat >/dev/null 2>&1 || true
launchctl kickstart "gui/$(id -u)/dev.syntopica.atrium-refresh" >/dev/null 2>&1 || true
exit 0
