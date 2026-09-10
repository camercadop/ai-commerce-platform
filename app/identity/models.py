import uuid

from sqlalchemy import UUID, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db import BaseModel, SoftDeleteMixin, TimestampMixin


class Customer(SoftDeleteMixin, TimestampMixin, BaseModel):
    """Represents a customer profile owned by the application.

    Identity and authentication are delegated to the external identity provider.
    This model owns domain-specific customer data linked to the provider via
    identity_provider_id, populated from the JWT subject claim.
    """

    __tablename__ = "identity_customers"

    __table_args__ = (
        Index(
            "idx_identity_customers_identity_provider_id",
            "identity_provider_id",
            unique=True,
        ),
        Index("idx_identity_customers_email", "email", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this customer.

    identity_provider_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Subject claim from the JWT issued by the identity provider. Used to link
    # this profile to the authenticated user without coupling to a specific provider.

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Customer email address, mirrored from the identity provider at registration.

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Customer's given name.

    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Customer's family name.

    addresses: Mapped[list[Address]] = relationship(
        "Address", back_populates="customer", cascade="all, delete-orphan"
    )
    # All addresses registered by this customer.

    preferences: Mapped[list[CustomerPreference]] = relationship(
        "CustomerPreference", back_populates="customer", cascade="all, delete-orphan"
    )
    # All preferences set by this customer.


class Address(SoftDeleteMixin, TimestampMixin, BaseModel):
    """A physical address associated with a customer.

    A customer may have multiple addresses. Only one address per customer
    may be marked as the default.
    """

    __tablename__ = "identity_customer_addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this address.

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "identity_customers.id", name="fk_identity_customer_addresses_customer_id"
        ),
        nullable=False,
    )
    # The customer this address belongs to.

    label: Mapped[str] = mapped_column(String(100), nullable=False)
    # User-defined label for this address (e.g. Home, Work).

    street: Mapped[str] = mapped_column(String(255), nullable=False)
    # Street line including number and street name.

    city: Mapped[str] = mapped_column(String(100), nullable=False)
    # City or locality.

    state: Mapped[str] = mapped_column(String(100), nullable=False)
    # State, province, or region.

    country: Mapped[str] = mapped_column(String(100), nullable=False)
    # Country name or ISO 3166-1 alpha-2 code.

    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    # Postal or ZIP code.

    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Whether this is the customer's default address for orders and shipping.

    customer: Mapped[Customer] = relationship("Customer", back_populates="addresses")
    # The customer this address belongs to.


class CustomerPreference(TimestampMixin, BaseModel):
    """A single key-value preference entry for a customer.

    Preferences are stored as individual rows to allow arbitrary extensibility
    without schema changes. Each key must be unique per customer.

    Examples: language=en, timezone=UTC, whatsapp_enabled=true.
    """

    __tablename__ = "identity_customer_preferences"

    __table_args__ = (
        UniqueConstraint(
            "customer_id",
            "key",
            name="uq_identity_customer_preferences_customer_id_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Unique identifier for this preference entry.

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "identity_customers.id",
            name="fk_identity_customer_preferences_customer_id",
        ),
        nullable=False,
    )
    # The customer this preference belongs to.

    key: Mapped[str] = mapped_column(Text, nullable=False)
    # Preference name (e.g. language, timezone, whatsapp_enabled).

    value: Mapped[str] = mapped_column(Text, nullable=False)
    # Preference value stored as plain text.

    customer: Mapped[Customer] = relationship("Customer", back_populates="preferences")
    # The customer this preference belongs to.
