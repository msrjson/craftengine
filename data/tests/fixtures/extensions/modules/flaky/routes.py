"""A route that always fails unexpectedly."""


def boom() -> str:
    """Fail the way a bug fails."""
    raise RuntimeError("flaky route")


def register(router: object) -> None:
    """Register the failing route."""
    router.get("/ext-test/flaky", boom)
