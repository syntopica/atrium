"""Run one parsed `curate-*` subcommand of the atrium CLI."""

from argparse import Namespace

from atrium.state.state_directory import state_directory


def run_curate_command(args: Namespace) -> int:
    """Dispatch the promotion pipeline's steps; each imports its own module lazily."""
    if args.command == "curate-screen":
        from atrium.curate.run_curate_screen_cli import run_curate_screen_cli

        return run_curate_screen_cli(state_directory() / "synthesis")
    if args.command == "curate-extract":
        from atrium.curate.run_curate_extract_cli import run_curate_extract_cli
        from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

        return run_curate_extract_cli(args.size, args.holdout, args.model or LOCAL_DEFAULT_MODEL)
    if args.command == "curate-cluster":
        from atrium.curate.run_curate_cluster_cli import run_curate_cluster_cli
        from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

        return run_curate_cluster_cli(
            args.threshold, args.neighbours, args.budget, args.model or LOCAL_DEFAULT_MODEL
        )
    if args.command == "curate-neighbours":
        from atrium.curate.run_curate_neighbours_cli import run_curate_neighbours_cli

        return run_curate_neighbours_cli(args.threshold, args.neighbours)
    if args.command == "curate-publishable":
        from atrium.curate.run_curate_publishable_cli import run_curate_publishable_cli
        from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

        return run_curate_publishable_cli(args.budget, args.model or LOCAL_DEFAULT_MODEL)
    if args.command == "curate-propose":
        from atrium.curate.run_curate_propose_cli import run_curate_propose_cli
        from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

        return run_curate_propose_cli(args.budget, args.model or LOCAL_DEFAULT_MODEL)
    raise ValueError(f"unknown curate command {args.command!r}")
