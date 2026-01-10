#!/usr/bin/env python
"""CLI commands for scheduled tasks."""
import click
from flask.cli import with_appcontext
from app.services.messaging import process_scheduled_messages, init_default_templates


@click.command('send-scheduled')
@with_appcontext
def send_scheduled_messages():
    """Process and send all pending scheduled messages."""
    count = process_scheduled_messages()
    click.echo(f'Processed {count} scheduled message(s)')


@click.command('init-templates')
@with_appcontext
def init_templates():
    """Initialize default message templates."""
    init_default_templates()
    click.echo('Message templates initialized')


def register_commands(app):
    """Register CLI commands with the app."""
    app.cli.add_command(send_scheduled_messages)
    app.cli.add_command(init_templates)
