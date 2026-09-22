import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.identity.exceptions import (
    AddressNotFound,
    CustomerAlreadyExists,
    CustomerNotFound,
    InvalidPreferenceKey,
)
from app.identity.service import AddressService, CustomerService
from app.identity.tests.fakes import (
    FakeAddressRepository,
    FakeAuditPort,
    FakeCustomerRepository,
    make_address,
    make_customer,
)


def _customer_service(
    customers: list | None = None,
    audit: FakeAuditPort | None = None,
) -> CustomerService:
    return CustomerService(
        repo=FakeCustomerRepository(customers),
        audit=audit or FakeAuditPort(),
    )


def _address_service(
    addresses: list | None = None,
    customers: list | None = None,
    audit: FakeAuditPort | None = None,
) -> AddressService:
    return AddressService(
        repo=FakeAddressRepository(addresses),
        customer_repo=FakeCustomerRepository(customers),
        audit=audit or FakeAuditPort(),
    )


class TestCustomerServiceRegister:
    def test_creates_customer(self) -> None:
        service = _customer_service()

        customer = service.register(
            identity_provider_id="sub-abc",
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
        )

        assert customer.identity_provider_id == "sub-abc"
        assert customer.email == "jane@example.com"

    def test_raises_if_already_exists(self) -> None:
        existing = make_customer(identity_provider_id="sub-abc")
        service = _customer_service([existing])

        with pytest.raises(CustomerAlreadyExists):
            service.register(
                identity_provider_id="sub-abc",
                email="other@example.com",
                first_name="John",
                last_name="Smith",
            )

    def test_raises_on_integrity_error(self) -> None:
        class _RaisingRepo(FakeCustomerRepository):
            def create(self, **kwargs: object) -> object:
                raise IntegrityError(None, None, Exception("unique"))

        service = CustomerService(repo=_RaisingRepo(), audit=FakeAuditPort())

        with pytest.raises(CustomerAlreadyExists):
            service.register(
                identity_provider_id="sub-new",
                email="new@example.com",
                first_name="New",
                last_name="User",
            )


class TestCustomerServiceGetProfile:
    def test_returns_customer(self) -> None:
        customer = make_customer()
        service = _customer_service([customer])

        result = service.get_profile(customer.id)

        assert result.id == customer.id

    def test_raises_if_not_found(self) -> None:
        service = _customer_service()

        with pytest.raises(CustomerNotFound):
            service.get_profile(uuid.uuid4())


class TestCustomerServiceUpdateProfile:
    def test_updates_fields(self) -> None:
        customer = make_customer(first_name="Jane")
        audit = FakeAuditPort()
        service = _customer_service([customer], audit)

        result = service.update_profile(customer.id, {"first_name": "Alice"})

        assert result.first_name == "Alice"

    def test_records_audit_entry(self) -> None:
        customer = make_customer(first_name="Jane")
        audit = FakeAuditPort()
        service = _customer_service([customer], audit)

        service.update_profile(customer.id, {"first_name": "Alice"})

        assert len(audit.recorded) == 1
        entry = audit.recorded[0]
        assert entry.action == "customer.profile_updated"
        assert entry.operation == "update"
        assert entry.aggregate_id == customer.id
        assert entry.changes is not None
        assert entry.changes["first_name"].before == "Jane"
        assert entry.changes["first_name"].after == "Alice"

    def test_raises_if_not_found(self) -> None:
        service = _customer_service()

        with pytest.raises(CustomerNotFound):
            service.update_profile(uuid.uuid4(), {"first_name": "Alice"})


class TestCustomerServiceUpdatePreferences:
    @pytest.fixture(autouse=True)
    def patch_preferences_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Replace _load_preferences_config with a controlled config for all tests in this class."""
        monkeypatch.setattr(
            "app.identity.service._load_preferences_config",
            lambda: {
                "language": {"is_private": False},
                "internal_score": {"is_private": True},
            },
        )

    def test_inserts_new_preferences(self) -> None:
        customer = make_customer()
        repo = FakeCustomerRepository([customer])
        audit = FakeAuditPort()
        service = CustomerService(repo=repo, audit=audit)

        service.update_preferences(customer.id, {"language": "en"})

        assert len(customer.preferences) == 1
        assert customer.preferences[0].key == "language"
        assert customer.preferences[0].value == "en"

    def test_updates_existing_preference(self) -> None:
        from app.identity.models import CustomerPreference

        pref = CustomerPreference()
        pref.key = "language"  # type: ignore[assignment]
        pref.value = "en"  # type: ignore[assignment]
        customer = make_customer(preferences=[pref])
        repo = FakeCustomerRepository([customer])
        audit = FakeAuditPort()
        service = CustomerService(repo=repo, audit=audit)

        service.update_preferences(customer.id, {"language": "es"})

        assert pref.value == "es"
        assert len(customer.preferences) == 1

    def test_records_audit_entry(self) -> None:
        customer = make_customer()
        audit = FakeAuditPort()
        service = _customer_service([customer], audit)

        service.update_preferences(customer.id, {"language": "en"})

        assert len(audit.recorded) == 1
        entry = audit.recorded[0]
        assert entry.action == "customer.preferences_updated"
        assert entry.operation == "update"
        assert entry.changes is not None
        assert entry.changes["language"].before is None
        assert entry.changes["language"].after == "en"

    def test_raises_if_customer_not_found(self) -> None:
        service = _customer_service()

        with pytest.raises(CustomerNotFound):
            service.update_preferences(uuid.uuid4(), {"language": "en"})

    def test_raises_on_unknown_preference_key(self) -> None:
        customer = make_customer()
        service = _customer_service([customer])

        with pytest.raises(InvalidPreferenceKey):
            service.update_preferences(customer.id, {"unknown_key": "value"})

    def test_raises_on_private_preference_key(self) -> None:
        customer = make_customer()
        service = _customer_service([customer])

        with pytest.raises(InvalidPreferenceKey):
            service.update_preferences(customer.id, {"internal_score": "42"})


class TestAddressServiceListAddresses:
    def test_returns_addresses(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=customer.id)
        audit = FakeAuditPort()
        service = _address_service([address], [customer], audit)

        result = service.list_addresses(customer.id)

        assert len(result) == 1
        assert result[0].id == address.id

    def test_raises_if_customer_not_found(self) -> None:
        service = _address_service()

        with pytest.raises(CustomerNotFound):
            service.list_addresses(uuid.uuid4())


class TestAddressServiceAddAddress:
    def test_creates_address(self) -> None:
        customer = make_customer()
        audit = FakeAuditPort()
        service = _address_service(customers=[customer], audit=audit)

        address = service.add_address(
            customer.id,
            label="Home",
            street="123 Main St",
            city="Springfield",
            state="IL",
            country="US",
            postal_code="62701",
            is_default=False,
        )

        assert address.customer_id == customer.id

    def test_records_audit_entry(self) -> None:
        customer = make_customer()
        audit = FakeAuditPort()
        service = _address_service(customers=[customer], audit=audit)

        address = service.add_address(
            customer.id,
            label="Home",
            street="123 Main St",
            city="Springfield",
            state="IL",
            country="US",
            postal_code="62701",
            is_default=False,
        )

        assert len(audit.recorded) == 1
        entry = audit.recorded[0]
        assert entry.action == "customer.address_created"
        assert entry.operation == "create"
        assert entry.aggregate_id == address.id
        assert entry.changes is not None
        assert entry.changes["label"].before is None
        assert entry.changes["label"].after == "Home"

    def test_returns_existing_address_without_audit(self) -> None:
        customer = make_customer()
        existing = make_address(customer_id=customer.id, label="Home")
        audit = FakeAuditPort()
        service = _address_service([existing], [customer], audit)

        result = service.add_address(
            customer.id,
            label="Home",
            street="123 Main St",
            city="Springfield",
            state="IL",
            country="US",
            postal_code="62701",
            is_default=False,
        )

        assert result.id == existing.id
        assert len(audit.recorded) == 0

    def test_raises_if_customer_not_found(self) -> None:
        service = _address_service()

        with pytest.raises(CustomerNotFound):
            service.add_address(uuid.uuid4(), label="Home", street="x", city="x",
                                state="x", country="x", postal_code="x")


class TestAddressServiceUpdateAddress:
    def test_updates_address(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=customer.id, city="Springfield")
        audit = FakeAuditPort()
        service = _address_service([address], [customer], audit)

        result = service.update_address(
            customer.id, address.id, {"city": "Shelbyville"}
        )

        assert result.city == "Shelbyville"

    def test_records_audit_entry(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=customer.id, city="Springfield")
        audit = FakeAuditPort()
        service = _address_service([address], [customer], audit)

        service.update_address(customer.id, address.id, {"city": "Shelbyville"})

        assert len(audit.recorded) == 1
        entry = audit.recorded[0]
        assert entry.action == "customer.address_updated"
        assert entry.operation == "update"
        assert entry.aggregate_id == address.id
        assert entry.changes is not None
        assert entry.changes["city"].before == "Springfield"
        assert entry.changes["city"].after == "Shelbyville"

    def test_raises_if_address_belongs_to_other_customer(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=uuid.uuid4())
        service = _address_service([address], [customer])

        with pytest.raises(AddressNotFound):
            service.update_address(customer.id, address.id, {"city": "x"})

    def test_clears_default_when_is_default_true(self) -> None:
        customer = make_customer()
        existing_default = make_address(customer_id=customer.id, label="Work", is_default=True)
        address = make_address(customer_id=customer.id, label="Home", is_default=False)
        service = _address_service([existing_default, address], [customer])

        service.update_address(customer.id, address.id, {"is_default": True})

        assert existing_default.is_default is False
        assert address.is_default is True

    def test_raises_if_customer_not_found(self) -> None:
        service = _address_service()

        with pytest.raises(CustomerNotFound):
            service.update_address(uuid.uuid4(), uuid.uuid4(), {"city": "x"})

    def test_raises_if_address_not_found(self) -> None:
        customer = make_customer()
        service = _address_service(customers=[customer])

        with pytest.raises(AddressNotFound):
            service.update_address(customer.id, uuid.uuid4(), {"city": "x"})


class TestAddressServiceRemoveAddress:
    def test_soft_deletes_address(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=customer.id)
        audit = FakeAuditPort()
        service = _address_service([address], [customer], audit)

        service.remove_address(customer.id, address.id)

        assert address.deleted_at is not None

    def test_records_audit_entry(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=customer.id)
        audit = FakeAuditPort()
        service = _address_service([address], [customer], audit)

        service.remove_address(customer.id, address.id)

        assert len(audit.recorded) == 1
        entry = audit.recorded[0]
        assert entry.action == "customer.address_deleted"
        assert entry.operation == "delete"
        assert entry.aggregate_id == address.id
        assert entry.changes is None

    def test_raises_if_not_found(self) -> None:
        customer = make_customer()
        service = _address_service(customers=[customer])

        with pytest.raises(AddressNotFound):
            service.remove_address(customer.id, uuid.uuid4())

    def test_raises_if_customer_not_found(self) -> None:
        service = _address_service()

        with pytest.raises(CustomerNotFound):
            service.remove_address(uuid.uuid4(), uuid.uuid4())

    def test_raises_if_address_belongs_to_other_customer(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=uuid.uuid4())
        service = _address_service([address], [customer])

        with pytest.raises(AddressNotFound):
            service.remove_address(customer.id, address.id)
