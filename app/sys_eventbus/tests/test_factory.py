import pytest

from app.shared.events import NoOpMessageBroker
from app.sys_eventbus.brokers import KafkaMessageBroker
from app.sys_eventbus.factory import resolve_broker


# ---------------------------------------------------------------------------
# resolve_broker
# ---------------------------------------------------------------------------


class TestResolveBroker:
    def test_returns_kafka_broker_when_env_var_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093")

        result = resolve_broker()

        assert isinstance(result, KafkaMessageBroker)

    def test_kafka_broker_uses_provided_bootstrap_servers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

        result = resolve_broker()

        assert isinstance(result, KafkaMessageBroker)
        assert result._bootstrap_servers == "kafka:9092"

    def test_kafka_broker_uses_custom_group_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093")

        result = resolve_broker(group_id="my-group")

        assert isinstance(result, KafkaMessageBroker)
        assert result._group_id == "my-group"

    def test_returns_noop_broker_when_env_var_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)

        result = resolve_broker()

        assert isinstance(result, NoOpMessageBroker)
