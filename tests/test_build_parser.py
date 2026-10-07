from pathlib import Path

import pytest

from atrium.cli_parser.build_parser import build_parser


def test_index_defaults_under_the_state_directory() -> None:
    parser = build_parser(Path("/state"), Path("/archive"), Path("/state/last-refresh"), None)
    args = parser.parse_args(["embed"])
    assert args.index == Path("/state/index.sqlite3")
    assert args.command == "embed"


def test_status_takes_resolved_paths_as_defaults() -> None:
    parser = build_parser(Path("/state"), Path("/archive"), Path("/state/last-refresh"), None)
    args = parser.parse_args(["status"])
    assert args.archive == Path("/archive")
    assert args.refresh_stamp == Path("/state/last-refresh")


def test_synthesize_defaults_to_the_agy_lane() -> None:
    parser = build_parser(Path("/state"), Path("/archive"), Path("/state/last-refresh"), None)
    args = parser.parse_args(["synthesize", "archive"])
    assert (args.producer, args.workers) == ("agy", 3)


def test_synthesize_scopes_are_mutually_exclusive() -> None:
    parser = build_parser(Path("/state"), Path("/archive"), Path("/state/last-refresh"), None)
    with pytest.raises(SystemExit):
        parser.parse_args(["synthesize", "a", "--project", "p", "--workspace", "w"])


def test_a_subcommand_is_required() -> None:
    parser = build_parser(Path("/state"), Path("/archive"), Path("/state/last-refresh"), None)
    with pytest.raises(SystemExit):
        parser.parse_args([])
