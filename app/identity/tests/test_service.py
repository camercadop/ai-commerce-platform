import uuid

import pytest

from app.identity.exceptions import (
    AddressNotFound,
    CustomerAlreadyExists,
    CustomerNotFound,
)
from app.identity.service import AddressService, CustomerService
from app.identity.tests.fakes import (
    FakeAddressRepository,
    FakeCustomerPreferenceSession,
    FakeCustomerRepository,
    make_address,
    make_customer,
)


class TestCustomerServiceRegister:
    def test_creates_customer(self) -> None:
        repo = FakeCustomerRepository()
        service = CustomerService.__new__(CustomerService)
        service.repo = repo
        service.session = FakeCustomerPreferenceSession()

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
        repo = FakeCustomerRepository([existing])
        service = CustomerService.__new__(CustomerService)
        service.repo = repo
        service.session = FakeCustomerPreferenceSession()

        with pytest.raises(CustomerAlreadyExists):
            service.register(
                identity_provider_id="sub-abc",
                email="other@example.com",
                first_name="John",
                last_name="Smith",
            )


class TestCustomerServiceGetProfile:
    def test_returns_customer(self) -> None:
        customer = make_customer()
        repo = FakeCustomerRepository([customer])
        service = CustomerService.__new__(CustomerService)
        service.repo = repo
        service.session = FakeCustomerPreferenceSession()

        result = service.get_profile(customer.id)

        assert result.id == customer.id

    def test_raises_if_not_found(self) -> None:
        repo = FakeCustomerRepository()
        service = CustomerService.__new__(CustomerService)
        service.repo = repo
        service.session = FakeCustomerPreferenceSession()

        with pytest.raises(CustomerNotFound):
            service.get_profile(uuid.uuid4())


class TestCustomerServiceUpdateProfile:
    def test_updates_fields(self) -> None:
        customer = make_customer(first_name="Jane")
        repo = FakeCustomerRepository([customer])
        service = CustomerService.__new__(CustomerService)
        service.repo = repo
        service.session = FakeCustomerPreferenceSession()

        result = service.update_profile(customer.id, {"first_name": "Alice"})

        assert result.first_name == "Alice"

    def test_raises_if_not_found(self) -> None:
        repo = FakeCustomerRepository()
        service = CustomerService.__new__(CustomerService)
        service.repo = repo
        service.session = FakeCustomerPreferenceSession()

        with pytest.raises(CustomerNotFound):
            service.update_profile(uuid.uuid4(), {"first_name": "Alice"})


class TestCustomerServiceUpdatePreferences:
    def test_inserts_new_preferences(self) -> None:
        customer = make_customer()
        repo = FakeCustomerRepository([customer])
        session = FakeCustomerPreferenceSession()
        service = CustomerService.__new__(CustomerService)
        service.repo = repo
        service.session = session

        service.update_preferences(customer.id, {"language": "en"})

        assert len(session.added) == 1
        assert session.added[0].key == "language"
        assert session.added[0].value == "en"

    def test_updates_existing_preference(self) -> None:
        from app.identity.models import CustomerPreference

        pref = CustomerPreference()
        pref.key = "language"  # type: ignore[assignment]
        pref.value = "en"  # type: ignore[assignment]
        customer = make_customer(preferences=[pref])
        repo = FakeCustomerRepository([customer])
        session = FakeCustomerPreferenceSession()
        service = CustomerService.__new__(CustomerService)
        service.repo = repo
        service.session = session

        service.update_preferences(customer.id, {"language": "es"})

        assert pref.value == "es"
        assert len(session.added) == 0

    def test_raises_if_customer_not_found(self) -> None:
        repo = FakeCustomerRepository()
        service = CustomerService.__new__(CustomerService)
        service.repo = repo
        service.session = FakeCustomerPreferenceSession()

        with pytest.raises(CustomerNotFound):
            service.update_preferences(uuid.uuid4(), {"language": "en"})


class TestAddressServiceListAddresses:
    def test_returns_addresses(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=customer.id)
        customer_repo = FakeCustomerRepository([customer])
        address_repo = FakeAddressRepository([address])
        service = AddressService.__new__(AddressService)
        service.repo = address_repo
        service.customer_repo = customer_repo

        result = service.list_addresses(customer.id)

        assert len(result) == 1
        assert result[0].id == address.id

    def test_raises_if_customer_not_found(self) -> None:
        service = AddressService.__new__(AddressService)
        service.repo = FakeAddressRepository()
        service.customer_repo = FakeCustomerRepository()

        with pytest.raises(CustomerNotFound):
            service.list_addresses(uuid.uuid4())


class TestAddressServiceAddAddress:
    def test_creates_address(self) -> None:
        customer = make_customer()
        service = AddressService.__new__(AddressService)
        service.repo = FakeAddressRepository()
        service.customer_repo = FakeCustomerRepository([customer])

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

    def test_raises_if_customer_not_found(self) -> None:
        service = AddressService.__new__(AddressService)
        service.repo = FakeAddressRepository()
        service.customer_repo = FakeCustomerRepository()

        with pytest.raises(CustomerNotFound):
            service.add_address(uuid.uuid4(), label="Home", street="x", city="x",
                                state="x", country="x", postal_code="x")


class TestAddressServiceUpdateAddress:
    def test_updates_address(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=customer.id, city="Springfield")
        service = AddressService.__new__(AddressService)
        service.repo = FakeAddressRepository([address])
        service.customer_repo = FakeCustomerRepository([customer])

        result = service.update_address(
            customer.id, address.id, {"city": "Shelbyville"}
        )

        assert result.city == "Shelbyville"

    def test_raises_if_address_belongs_to_other_customer(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=uuid.uuid4())
        service = AddressService.__new__(AddressService)
        service.repo = FakeAddressRepository([address])
        service.customer_repo = FakeCustomerRepository([customer])

        with pytest.raises(AddressNotFound):
            service.update_address(customer.id, address.id, {"city": "x"})


class TestAddressServiceRemoveAddress:
    def test_soft_deletes_address(self) -> None:
        customer = make_customer()
        address = make_address(customer_id=customer.id)
        service = AddressService.__new__(AddressService)
        service.repo = FakeAddressRepository([address])
        service.customer_repo = FakeCustomerRepository([customer])

        service.remove_address(customer.id, address.id)

        assert address.deleted_at is not None

    def test_raises_if_not_found(self) -> None:
        customer = make_customer()
        service = AddressService.__new__(AddressService)
        service.repo = FakeAddressRepository()
        service.customer_repo = FakeCustomerRepository([customer])

        with pytest.raises(AddressNotFound):
            service.remove_address(customer.id, uuid.uuid4())
