"""The `rekey-synthesis` handler of the atrium CLI."""

from pathlib import Path

from atrium.synthesize.default_registry import default_registry


def run_rekey_synthesis(*, apply: bool, repair: bool = False, archive: Path | None = None) -> int:
    """Move every pre-schema-2 record onto the identity the archive now implies.

    Reports before it writes, because the registry holds model output that was
    paid for once and cannot be regenerated for free.
    """
    from atrium.synthesize.rekey_synthesis_registry import rekey_synthesis_registry

    if repair:
        from atrium.synthesize.repair_mis_stamped_records import repair_mis_stamped_records

        assert archive is not None
        found = repair_mis_stamped_records(default_registry(), archive, apply=apply)
        verb = "repaired" if apply else "would repair"
        print(
            f"  {verb} {found['repaired']} mis-stamped records, "
            f"{found['intact']} already agree with the archive"
        )
        if found["unexplained"]:
            print(f"  {found['unexplained']} cite events absent under either rule; left alone")
        return 0

    report = rekey_synthesis_registry(default_registry(), apply=apply)
    verb = "re-keyed" if apply else "would re-key"
    print(f"  {verb} {report['moved']} records, {report['already']} already current")
    if report["backup"]:
        print(f"  records copied to {report['backup']} before rewriting")
    if report["collided"]:
        print(f"  {report['collided']} collided and were left alone: {report['collisions']}")
        return 1
    if not apply:
        print("  nothing written; pass --apply to write")
    return 0
