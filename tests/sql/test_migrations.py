from pytest_alembic import create_alembic_fixture, tests

alembic = create_alembic_fixture({"file": "migrations/alembic.ini"})


def test_model_definitions_match_ddl(alembic: object) -> None:
    tests.test_model_definitions_match_ddl(alembic)


def test_single_head_revision(alembic: object) -> None:
    tests.test_single_head_revision(alembic)


def test_up_down_consistency(alembic: object) -> None:
    tests.test_up_down_consistency(alembic)


def test_upgrade(alembic: object) -> None:
    tests.test_upgrade(alembic)
