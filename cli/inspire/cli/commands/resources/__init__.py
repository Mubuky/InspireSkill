"""Resource commands for Inspire CLI."""

from __future__ import annotations

import click

from .resources_list import list_resources
from .resources_nodes import list_nodes
from .resources_specs import list_specs


@click.group()
def resources() -> None:
    """Inspect live compute availability and valid quota triples.

    Use `resources list` for current free / used capacity, `resources nodes`
    before multi-node GPU jobs that need whole 8-GPU nodes, and
    `resources specs` before any create command to choose a valid
    `--quota gpu,cpu,mem` triple for notebook / job / hpc / ray / serving.

    \b
    Examples:
        inspire resources specs --usage notebook --workspace CPU资源空间
        inspire resources specs --usage job --workspace 分布式训练空间 --group H200
        inspire resources list --all --include-cpu
        inspire resources nodes --min-nodes 2 --group H200
    """
    pass


resources.add_command(list_resources)
resources.add_command(list_nodes)
resources.add_command(list_specs)
