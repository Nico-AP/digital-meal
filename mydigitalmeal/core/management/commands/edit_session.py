import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string


def get_nested(d, keys):
    """Traverse nested dict by list of keys."""
    for key in keys:
        if not isinstance(d, dict) or key not in d:
            return None
        d = d[key]
    return d


def set_nested(d, keys, value):
    """Set a value in a nested dict, creating intermediate dicts as needed."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


class Command(BaseCommand):
    """Implemented to update session data to test TikTok integration."""

    help = "Interactively inspect and edit Django session data"

    def handle(self, *args, **options):  # noqa: C901, PLR0912, PLR0915
        SessionStore = import_string(settings.SESSION_ENGINE + ".SessionStore")  # noqa: N806

        # --- Step 1: Get session ID ---
        session_id = input("Enter session ID: ").strip()
        if not session_id:
            self.stderr.write("No session ID provided. Aborting.")
            return

        session = SessionStore(session_key=session_id)
        session_dict = dict(session)

        if not session_dict:
            self.stdout.write(self.style.WARNING("Session is empty or does not exist."))
        else:
            self.stdout.write("\nCurrent session data:")
            self.stdout.write(json.dumps(session_dict, indent=2, default=str))

        # --- Step 2: Edit loop ---
        while True:
            self.stdout.write(
                "\nOptions: [s]et a value | [d]elete a key | [v]iew session | [q]uit & save | [a]bort"  # noqa: E501
            )
            choice = input("Choice: ").strip().lower()

            if choice == "q":
                session.save()
                self.stdout.write(self.style.SUCCESS("\nSession saved. Final data:"))
                self.stdout.write(json.dumps(dict(session), indent=2, default=str))
                break

            if choice == "a":
                self.stdout.write(self.style.WARNING("Aborted. No changes saved."))
                break

            if choice == "v":
                self.stdout.write(json.dumps(dict(session), indent=2, default=str))

            elif choice == "s":
                key_path = input(
                    "  Key path (use dot notation for nested keys, e.g. portability.tiktok_open_id): "  # noqa: E501
                ).strip()
                if not key_path:
                    self.stderr.write("  Empty key path, skipping.")
                    continue

                keys = key_path.split(".")
                raw_value = input(
                    '  New value (enter raw JSON, e.g. "string", 42, true, {"a": 1}): '
                ).strip()

                try:
                    value = json.loads(raw_value)
                except json.JSONDecodeError:
                    # Treat as plain string if not valid JSON
                    value = raw_value
                    self.stdout.write(f'  Treating as plain string: "{value}"')

                if len(keys) == 1:
                    session[keys[0]] = value
                else:
                    # For nested keys, mutate the top-level dict and reassign
                    top = session.get(keys[0], {})
                    set_nested({keys[0]: top}, keys, value)
                    # set_nested works in-place on the top-level value
                    set_nested(top, keys[1:], value)
                    session[keys[0]] = top

                self.stdout.write(self.style.SUCCESS(f"  Set {key_path} = {value}"))

            elif choice == "d":
                key_path = input("  Key path to delete (dot notation): ").strip()
                if not key_path:
                    self.stderr.write("  Empty key path, skipping.")
                    continue

                keys = key_path.split(".")
                if len(keys) == 1:
                    if keys[0] in session:
                        del session[keys[0]]
                        self.stdout.write(self.style.SUCCESS(f"  Deleted '{keys[0]}'"))
                    else:
                        self.stderr.write(f"  Key '{keys[0]}' not found.")
                else:
                    parent = get_nested(dict(session), keys[:-1])
                    if parent is not None and keys[-1] in parent:
                        top = session[keys[0]]
                        # Navigate and delete
                        node = top
                        for k in keys[1:-1]:
                            node = node[k]
                        del node[keys[-1]]
                        session[keys[0]] = top
                        self.stdout.write(self.style.SUCCESS(f"  Deleted '{key_path}'"))
                    else:
                        self.stderr.write(f"  Key path '{key_path}' not found.")

            else:
                self.stderr.write("  Unknown option.")
