from importlib.metadata import version

from small_agent import __version__


def test_runtime_version_matches_package_metadata() -> None:
    assert __version__ == version("small-agent")
