"""SSH-related notebook command group."""

from __future__ import annotations

import click

from .connection_test_cmd import tunnel_test as _connection_test
from .forget_cmd import tunnel_remove as _forget
from .notebook_commands import ssh_notebook_cmd
from .refresh_cmd import tunnel_update as _refresh


@click.group("ssh")
def notebook_ssh() -> None:
    """Manage cached SSH connections for notebooks.

    One notebook name maps to at most one cached SSH connection. Use
    `ssh connect` to create or refresh it, and `ssh test` to diagnose it.
    """


notebook_ssh.add_command(ssh_notebook_cmd, name="connect")
notebook_ssh.add_command(_refresh, name="refresh")
notebook_ssh.add_command(_forget, name="forget")
notebook_ssh.add_command(_connection_test, name="test")


__all__ = ["notebook_ssh"]
