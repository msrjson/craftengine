"""A module that fails while it loads."""


def register(context: object) -> None:
    """Fail at load time; the manager must mark it failed and keep booting."""
    raise RuntimeError("broken at load")
