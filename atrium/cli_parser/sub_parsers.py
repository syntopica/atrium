"""The type of the object `ArgumentParser.add_subparsers` returns."""

import argparse
from typing import TypeAlias

# argparse exports no public name for it, and the real class cannot be subscripted at runtime.
SubParsers: TypeAlias = "argparse._SubParsersAction[argparse.ArgumentParser]"
