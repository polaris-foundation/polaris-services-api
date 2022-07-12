import time

import neo4j
import pytest
from mock import Mock, call
from neobolt.exceptions import TransientError
from pytest_mock import MockerFixture
from tenacity import stop_after_attempt

from dhos_services_api import neodb


@pytest.mark.usefixtures("app")
class TestNeodbRetry:
    @pytest.fixture(autouse=True)
    def mock_time_sleep(self, mocker: MockerFixture) -> Mock:
        return mocker.patch.object(time, "sleep")

    @pytest.fixture
    def mock_retry_sleep(self, mocker: MockerFixture) -> Mock:
        return mocker.patch.object(neodb.db.cypher_query.retry, "sleep")

    def test_neodb_retry_success(self, mock_retry_sleep: Mock) -> None:
        neodb.db.cypher_query("MATCH (r:Random) RETURN r")
        mock_retry_sleep.assert_not_called()

    def test_neodb_retry_config(self) -> None:
        assert neodb.db.cypher_query.retry.reraise
        assert neodb.db.cypher_query.retry.retry.exception_types is TransientError
        assert isinstance(neodb.db.cypher_query.retry.stop, stop_after_attempt)
        assert neodb.db.cypher_query.retry.stop.max_attempt_number == 3

    def test_neodb_retry_failure(
        self, mocker: MockerFixture, mock_retry_sleep: Mock
    ) -> None:
        mocker.patch.object(neo4j.Session, "run", side_effect=TransientError)
        with pytest.raises(TransientError):
            neodb.db.cypher_query("MATCH (r:Random) RETURN r")

        assert mock_retry_sleep.call_count == 2
        assert all(call(i) in mock_retry_sleep.mock_calls for i in (1, 2))
