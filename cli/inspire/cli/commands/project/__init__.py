"""Project management commands.

Usage:
    inspire project list
    inspire project detail <project-name>
    inspire project owners
"""

from __future__ import annotations

import click

from .project_commands import detail_project_cmd, list_projects_cmd, owners_project_cmd


@click.group()
def project():
    """View project quota, budget, priority, and owner metadata.

    Use this before creating GPU or CPU workloads to choose the project that
    still has usable budget / GPU quota and to confirm the maximum priority
    the selected project can request.

    \b
    Examples:
        inspire project list                # quota table
        inspire project list --json         # JSON with all fields
        inspire project detail <project-name> # single-project detail
        inspire project owners              # "负责人" dropdown contents
    """
    pass


project.add_command(list_projects_cmd)
project.add_command(detail_project_cmd)
project.add_command(owners_project_cmd)
