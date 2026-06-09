from .core import AIBenchmark


def create_app():
    from .app import create_app as _create_app

    return _create_app()


def __getattr__(name: str):
    if name == "app":
        from .app import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["AIBenchmark", "app", "create_app"]
