# Copyright (c) Amber Brown, 2018
# See LICENSE for details.

from __future__ import absolute_import, division

import os
import sys

import click

from subprocess import CalledProcessError, check_output, STDOUT

from ._settings import load_config_from_options
from ._builder import find_fragments


def _run(args, **kwargs):
    kwargs["stderr"] = STDOUT
    return check_output(args, **kwargs)


@click.command(name="check")
@click.option("--compare-with", default="origin/master")
@click.option("--dir", "directory", default=None)
@click.option("--config", "config", default=None)
def _main(compare_with, directory, config):
    return __main(compare_with, directory, config)


def __main(comparewith, directory, config):

    base_directory, config = load_config_from_options(directory, config)

    try:
        files_changed = (
            _run(
                ["git",
                 "diff",
                 "--name-only",
                 # Only show files that were Added (A), Copied (C), Modified (M)
                 # or Renamed (R).
                 "--diff-filter=ACMR",
                 comparewith + "..."
                ],
                cwd=base_directory
            )
            .decode(getattr(sys.stdout, "encoding", "utf8"))
            .strip()
        )
    except CalledProcessError as e:
        click.echo("git produced output while failing:")
        click.echo(e.output)
        raise

    # Convert changed files to a list.
    files_changed = files_changed.split(os.linesep) if files_changed else []

    # Create a set of changed files converted to absolute paths.
    files = set(os.path.join(base_directory, f) for f in files_changed)

    # Filter out ignored files.
    ignore_files = set(os.path.join(base_directory, f) for f in config["check_ignore_files"])
    if ignore_files:
        click.echo("Ignoring files:")
        for n, f in enumerate(ignore_files, start=1):
            click.echo("{}. {}".format(n, f))
        click.echo()

        files = set(f for f in files if f not in ignore_files)

    if len(files) == 0:
        click.echo("On trunk, or no diffs, so no newsfragment required.")
        sys.exit(0)

    click.echo("Looking at these files:")
    for n, f in enumerate(files, start=1):
        click.echo("{}. {}".format(n, f))
    click.echo()

    if len(files) == 1 and files.pop() == os.path.join(base_directory, config["filename"]):
        click.echo("Only the configured news file has changed.")
        sys.exit(0)

    fragments = set()

    if config.get("directory"):
        fragment_base_directory = os.path.abspath(config["directory"])
        fragment_directory = None
    else:
        fragment_base_directory = os.path.abspath(
            os.path.join(base_directory, config["package_dir"], config["package"])
        )
        fragment_directory = "newsfragments"

    fragments = set(
        find_fragments(
            fragment_base_directory,
            config["sections"],
            fragment_directory,
            config["types"],
        )[1]
    )
    fragments_in_branch = fragments & files

    if not fragments_in_branch:
        click.echo("No new newsfragments found on this branch.")
        sys.exit(1)
    else:
        click.echo("Found:")
        for n, fragment in enumerate(fragments_in_branch, start=1):
            click.echo("{}. {}".format(n, fragment))
        sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    _main()
