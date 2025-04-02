from __future__ import annotations

from argparse import ArgumentParser, ArgumentTypeError
from secrets import token_urlsafe
from typing import Any
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from hc.accounts.forms import LowercaseEmailField
from hc.accounts.models import Project


def _new_key(nbytes: int = 24) -> str:
    while True:
        candidate = token_urlsafe(nbytes)
        if candidate[0] not in "-_" and candidate[-1] not in "-_":
            return candidate


def str_to_bool(value: str) -> bool:
    """Converts 'true'/'false' strings (case-insensitive) to booleans."""
    if isinstance(value, bool):
        return value
    if value.lower() in ("true", "t", "yes", "y", "1"):
        return True
    elif value.lower() in ("false", "f", "no", "n", "0"):
        return False
    else:
        raise ArgumentTypeError(f"Boolean value expected (true/false), got '{value}'")


class Command(BaseCommand):
    help = """Create a project for a specified user.
    Optionally enable and generate API keys and/or a ping key by setting the
    corresponding options to 'true'."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            "--enable-api-key",
            type=str_to_bool,
            default=False,
            metavar="true|false",
            help="Generate and enable the writeable API key ('true' or 'false'). Default: false.",
        )

        parser.add_argument(
            "--enable-readonly-api-key",
            type=str_to_bool,
            default=False,
            metavar="true|false",
            help="Generate and enable the read-only API key ('true' or 'false'). Default: false.",
        )

        parser.add_argument(
            "--enable-ping-key",
            type=str_to_bool,
            default=False,
            metavar="true|false",
            help="Generate and enable the ping key ('true' or 'false'). Default: false.",
        )

    def handle(self, *args: Any, **options: Any) -> str:
        project = None
        owner = None

        while not owner:
            raw = input("Owner's email address: ")
            try:
                email = LowercaseEmailField().clean(raw)
            except ValidationError as e:
                self.stderr.write("Error: " + " ".join(e.messages))
                continue
            try:
                owner = User.objects.get(email=email)
            except User.DoesNotExist as e:
                self.stderr.write(f"Error: User with email {email} not found.")
                continue

        raw = input("Project: ")
        name = raw.strip()

        try:
            project = Project(owner=owner, name=name)

            project.badge_key = str(uuid4())

            if options["enable_api_key"]:
                project.api_key = _new_key(24)

            if options["enable_readonly_api_key"]:
                project.api_key_readonly = _new_key(24)

            if options["enable_ping_key"]:
                project.ping_key = _new_key(16)

            project.save()

            return f"Project '{name}' created successfully for {owner.email}."

        except Exception as e:
            self.stderr.write(f"Error creating project: {e}")
            return "Project creation failed."
