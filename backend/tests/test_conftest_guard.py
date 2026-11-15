import pytest

from tests.conftest import require_local_database


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@localhost:5432/nfl",
        "postgresql+psycopg://u:p@127.0.0.1/nfl",
        "postgresql+psycopg://u:p@db:5432/nfl",
    ],
)
def test_local_databases_are_allowed(url: str) -> None:
    require_local_database(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@ep-cool-name-123.us-east-2.aws.neon.tech/nfl",
        "postgresql+psycopg://u:p@localhost.attacker.example/nfl",
    ],
)
def test_remote_databases_stop_the_run(url: str) -> None:
    with pytest.raises(pytest.exit.Exception):
        require_local_database(url)
