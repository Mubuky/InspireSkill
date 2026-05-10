"""Notebook / Interactive instance commands.

Usage:
    inspire notebook list
    inspire notebook status <name>
    inspire notebook create --quota 1,20,200
    inspire notebook stop <name>
    inspire notebook ssh connect <notebook>     # establish cached connection
    inspire notebook exec <notebook> "<cmd>"
    inspire notebook scp <notebook> <src> <dst>
"""

from __future__ import annotations

import click

from inspire.cli.commands.batch import notebook_batch
from inspire.cli.commands.workload_profile import make_profile_command

from .notebook_commands import (
    create_notebook_cmd,
    delete_notebook_cmd,
    list_notebooks,
    notebook_id_cmd,
    notebook_status,
    start_notebook_cmd,
    stop_notebook_cmd,
)
from .path_aliases import path_aliases_cmd
from .ssh import notebook_ssh
from .notebook_events import events as notebook_events
from .notebook_lifecycle import lifecycle as notebook_lifecycle
from .notebook_metrics import notebook_metrics

# Remote operations on a cached notebook connection.
from .install_deps import install_deps_cmd
from .remote_exec import exec_command as _remote_exec
from .remote_scp import bridge_scp as _remote_scp
from .remote_shell import bridge_ssh as _remote_shell


@click.group()
def notebook():
    """Manage notebook/interactive instances.

    \b
    Examples:
        inspire notebook list                          # List all instances
        inspire notebook ssh connect <notebook>        # Establish cached connection
        inspire notebook exec <notebook> "nvidia-smi"  # Run a remote command
        inspire notebook metrics <notebook> --window 30m
    """
    pass


# Core lifecycle (existing).
notebook.add_command(list_notebooks)            # list
notebook.add_command(notebook_status)           # status
notebook.add_command(notebook_id_cmd)           # id
notebook.add_command(create_notebook_cmd)       # create
notebook.add_command(make_profile_command("notebook"))  # profile
notebook.add_command(notebook_batch)            # batch
notebook.add_command(stop_notebook_cmd)         # stop
notebook.add_command(start_notebook_cmd)        # start
notebook.add_command(delete_notebook_cmd)       # delete
notebook.add_command(notebook_ssh)              # ssh
notebook.add_command(notebook_events)           # events (K8s scheduling / pod lifecycle)
notebook.add_command(notebook_lifecycle)        # lifecycle (run-cycle timeline; /run_index/list)
notebook.add_command(notebook_metrics)          # metrics (资源视图 time-series, no SSH needed)
notebook.add_command(path_aliases_cmd)          # path (project remote path aliases)

# Remote operations on a cached notebook connection.
notebook.add_command(_remote_exec,  name="exec")
notebook.add_command(_remote_scp,   name="scp")
notebook.add_command(_remote_shell, name="shell")
notebook.add_command(install_deps_cmd, name="install-deps")
