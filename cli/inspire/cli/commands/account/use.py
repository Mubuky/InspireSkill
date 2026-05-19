"""``inspire account use <name>`` — switch the active account."""

from __future__ import annotations

import click

from inspire.accounts import AccountError, current_account, set_current_account


@click.command("use")
@click.argument("name")
def use(name: str) -> None:
    """Switch the active account.

    Updates ``~/.inspire/current`` so every subsequent ``inspire`` command
    resolves its config, cached notebook SSH entries, rtunnel proxy state,
    and login cache under ``~/.inspire/accounts/<name>/``. The switched-away
    account's files are preserved for quick switch-back.
    """
    try:
        set_current_account(name)
    except AccountError as err:
        raise click.ClickException(str(err)) from err
    click.echo(f"Active account: {current_account() or name.strip()}")
