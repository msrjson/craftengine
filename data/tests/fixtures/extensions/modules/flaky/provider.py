"""A module whose listener and route always fail unexpectedly."""


def explode(event: object) -> None:
    """Fail the way a bug fails: an untyped exception."""
    raise RuntimeError("flaky listener")


def register(context: object) -> None:
    """Listen to a test event with a listener that always raises."""
    context.listen("ext_test.pinged", explode)
