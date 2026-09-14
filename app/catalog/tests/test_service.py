import uuid

import pytest

from app.catalog.exceptions import (
    BrandAlreadyExists,
    BrandNotFound,
    CategoryAlreadyExists,
    CategoryAttributeAlreadyExists,
    CategoryAttributeNotFound,
    CategoryNotFound,
    InvalidVariantAttributes,
    ProductAlreadyExists,
    ProductNotFound,
    VariantAlreadyExists,
    VariantNotFound,
)
from app.catalog.service import (
    BrandService,
    CategoryAttributeService,
    CategoryService,
    ProductService,
    VariantService,
    _publish,
)
from app.catalog.tests.fakes import (
    FakeAuditPort,
    FakeBrandRepository,
    FakeCategoryAttributeRepository,
    FakeCategoryRepository,
    FakeProductRepository,
    FakeVariantRepository,
    IntegrityErrorAttributeRepository,
    IntegrityErrorBrandRepository,
    IntegrityErrorCategoryRepository,
    IntegrityErrorProductRepository,
    IntegrityErrorVariantRepository,
    RaisingMessageBroker,
    make_brand,
    make_category,
    make_category_attribute,
    make_product,
    make_variant,
)
from app.shared.events import EventEnvelope, NoOpMessageBroker

_ACTOR = uuid.UUID(int=0)


# ---------------------------------------------------------------------------
# _publish
# ---------------------------------------------------------------------------


class TestPublish:
    def test_swallows_broker_exception(self) -> None:
        _publish(
            RaisingMessageBroker(),
            "catalog.category.created",
            "CategoryCreated",
            "category",
            uuid.uuid4(),
            {},
            "",
        )


def _category_service(
    categories: list | None = None,
) -> CategoryService:
    svc = CategoryService.__new__(CategoryService)
    svc.repo = FakeCategoryRepository(categories)
    svc._audit = FakeAuditPort()
    svc._broker = NoOpMessageBroker()
    return svc


def _brand_service(brands: list | None = None) -> BrandService:
    svc = BrandService.__new__(BrandService)
    svc.repo = FakeBrandRepository(brands)
    svc._audit = FakeAuditPort()
    svc._broker = NoOpMessageBroker()
    return svc


def _product_service(
    products: list | None = None,
    categories: list | None = None,
    brands: list | None = None,
) -> ProductService:
    svc = ProductService.__new__(ProductService)
    svc.repo = FakeProductRepository(products)
    svc._category_repo = FakeCategoryRepository(categories)
    svc._brand_repo = FakeBrandRepository(brands)
    svc._audit = FakeAuditPort()
    svc._broker = NoOpMessageBroker()
    return svc


def _variant_service(
    variants: list | None = None,
    products: list | None = None,
    categories: list | None = None,
    attributes: list | None = None,
) -> VariantService:
    svc = VariantService.__new__(VariantService)
    svc.repo = FakeVariantRepository(variants)
    svc._product_repo = FakeProductRepository(products)
    svc._category_repo = FakeCategoryRepository(categories)
    svc._attr_repo = FakeCategoryAttributeRepository(attributes)
    svc._audit = FakeAuditPort()
    svc._broker = NoOpMessageBroker()
    return svc


def _attribute_service(
    attributes: list | None = None,
    categories: list | None = None,
) -> CategoryAttributeService:
    svc = CategoryAttributeService.__new__(CategoryAttributeService)
    svc.repo = FakeCategoryAttributeRepository(attributes)
    svc._category_repo = FakeCategoryRepository(categories)
    svc._audit = FakeAuditPort()
    svc._broker = NoOpMessageBroker()
    return svc


# ---------------------------------------------------------------------------
# CategoryService
# ---------------------------------------------------------------------------


class TestCategoryServiceCreate:
    def test_creates_category(self) -> None:
        svc = _category_service()

        result = svc.create(_ACTOR, name="Electronics")

        assert result.name == "Electronics"
        assert result.parent_id is None

    def test_raises_if_already_exists(self) -> None:
        existing = make_category(name="Electronics")
        svc = _category_service([existing])

        with pytest.raises(CategoryAlreadyExists):
            svc.create(_ACTOR, name="Electronics")

    def test_raises_if_parent_not_found(self) -> None:
        svc = _category_service()

        with pytest.raises(CategoryNotFound):
            svc.create(_ACTOR, name="Phones", parent_id=uuid.uuid4())

    def test_raises_on_integrity_error_create(self) -> None:
        svc = _category_service()
        svc.repo = IntegrityErrorCategoryRepository()

        with pytest.raises(CategoryAlreadyExists):
            svc.create(_ACTOR, name="Electronics")


class TestCategoryServiceGet:
    def test_returns_category(self) -> None:
        cat = make_category()
        svc = _category_service([cat])

        assert svc.get(cat.id).id == cat.id

    def test_raises_if_not_found(self) -> None:
        svc = _category_service()

        with pytest.raises(CategoryNotFound):
            svc.get(uuid.uuid4())


class TestCategoryServiceUpdate:
    def test_updates_name(self) -> None:
        cat = make_category(name="Old")
        svc = _category_service([cat])

        result = svc.update(_ACTOR, cat.id, {"name": "New"})

        assert result.name == "New"

    def test_raises_if_not_found(self) -> None:
        svc = _category_service()

        with pytest.raises(CategoryNotFound):
            svc.update(_ACTOR, uuid.uuid4(), {"name": "x"})

    def test_raises_if_already_exists(self) -> None:
        cat1 = make_category(name="Electronics")
        cat2 = make_category(name="Clothing")
        svc = _category_service([cat1, cat2])

        with pytest.raises(CategoryAlreadyExists):
            svc.update(_ACTOR, cat2.id, {"name": "Electronics"})

    def test_raises_on_integrity_error_update(self) -> None:
        cat = make_category(name="Electronics")
        svc = _category_service([cat])
        svc.repo = IntegrityErrorCategoryRepository([cat])

        with pytest.raises(CategoryAlreadyExists):
            svc.update(_ACTOR, cat.id, {"name": "Other"})


class TestCategoryServiceDelete:
    def test_soft_deletes(self) -> None:
        cat = make_category()
        svc = _category_service([cat])

        svc.delete(_ACTOR, cat.id)

        assert cat.deleted_at is not None

    def test_raises_if_not_found(self) -> None:
        svc = _category_service()

        with pytest.raises(CategoryNotFound):
            svc.delete(_ACTOR, uuid.uuid4())


# ---------------------------------------------------------------------------
# BrandService
# ---------------------------------------------------------------------------


class TestBrandServiceCreate:
    def test_creates_brand(self) -> None:
        svc = _brand_service()

        result = svc.create(_ACTOR, name="Acme")

        assert result.name == "Acme"

    def test_raises_if_already_exists(self) -> None:
        existing = make_brand(name="Acme")
        svc = _brand_service([existing])

        with pytest.raises(BrandAlreadyExists):
            svc.create(_ACTOR, name="Acme")

    def test_raises_on_integrity_error_create(self) -> None:
        svc = _brand_service()
        svc.repo = IntegrityErrorBrandRepository()

        with pytest.raises(BrandAlreadyExists):
            svc.create(_ACTOR, name="Acme")


class TestBrandServiceGet:
    def test_returns_brand(self) -> None:
        brand = make_brand()
        svc = _brand_service([brand])

        assert svc.get(brand.id).id == brand.id

    def test_raises_if_not_found(self) -> None:
        svc = _brand_service()

        with pytest.raises(BrandNotFound):
            svc.get(uuid.uuid4())


class TestBrandServiceUpdate:
    def test_updates_name(self) -> None:
        brand = make_brand(name="Old")
        svc = _brand_service([brand])

        result = svc.update(_ACTOR, brand.id, {"name": "New"})

        assert result.name == "New"

    def test_raises_if_not_found(self) -> None:
        svc = _brand_service()

        with pytest.raises(BrandNotFound):
            svc.update(_ACTOR, uuid.uuid4(), {"name": "x"})

    def test_raises_if_already_exists(self) -> None:
        brand1 = make_brand(name="Acme")
        brand2 = make_brand(name="Other")
        svc = _brand_service([brand1, brand2])

        with pytest.raises(BrandAlreadyExists):
            svc.update(_ACTOR, brand2.id, {"name": "Acme"})

    def test_raises_on_integrity_error_update(self) -> None:
        brand = make_brand(name="Acme")
        svc = _brand_service([brand])
        svc.repo = IntegrityErrorBrandRepository([brand])

        with pytest.raises(BrandAlreadyExists):
            svc.update(_ACTOR, brand.id, {"name": "Other"})


class TestBrandServiceDelete:
    def test_soft_deletes(self) -> None:
        brand = make_brand()
        svc = _brand_service([brand])

        svc.delete(_ACTOR, brand.id)

        assert brand.deleted_at is not None

    def test_raises_if_not_found(self) -> None:
        svc = _brand_service()

        with pytest.raises(BrandNotFound):
            svc.delete(_ACTOR, uuid.uuid4())


# ---------------------------------------------------------------------------
# ProductService
# ---------------------------------------------------------------------------


class TestProductServiceCreate:
    def test_creates_product(self) -> None:
        svc = _product_service()

        result = svc.create(_ACTOR, sku="SKU-1", name="Widget", base_price="9.99")

        assert result.sku == "SKU-1"

    def test_raises_if_sku_exists(self) -> None:
        existing = make_product(sku="SKU-1")
        svc = _product_service([existing])

        with pytest.raises(ProductAlreadyExists):
            svc.create(_ACTOR, sku="SKU-1", name="Other", base_price="1.00")

    def test_raises_if_category_not_found(self) -> None:
        svc = _product_service()

        with pytest.raises(CategoryNotFound):
            svc.create(
                _ACTOR,
                sku="SKU-1",
                name="x",
                base_price="1.00",
                category_id=uuid.uuid4(),
            )

    def test_raises_if_brand_not_found(self) -> None:
        svc = _product_service()

        with pytest.raises(BrandNotFound):
            svc.create(
                _ACTOR, sku="SKU-1", name="x", base_price="1.00", brand_id=uuid.uuid4()
            )

    def test_raises_on_integrity_error_create(self) -> None:
        svc = _product_service()
        svc.repo = IntegrityErrorProductRepository()

        with pytest.raises(ProductAlreadyExists):
            svc.create(_ACTOR, sku="SKU-1", name="Widget", base_price="9.99")


class TestProductServiceGet:
    def test_returns_product(self) -> None:
        product = make_product()
        svc = _product_service([product])

        assert svc.get(product.id).id == product.id

    def test_raises_if_not_found(self) -> None:
        svc = _product_service()

        with pytest.raises(ProductNotFound):
            svc.get(uuid.uuid4())


class TestProductServiceUpdate:
    def test_updates_name(self) -> None:
        product = make_product(name="Old")
        svc = _product_service([product])

        result = svc.update(_ACTOR, product.id, {"name": "New"})

        assert result.name == "New"

    def test_raises_if_not_found(self) -> None:
        svc = _product_service()

        with pytest.raises(ProductNotFound):
            svc.update(_ACTOR, uuid.uuid4(), {"name": "x"})

    def test_raises_if_sku_already_exists(self) -> None:
        p1 = make_product(sku="SKU-1")
        p2 = make_product(sku="SKU-2")
        svc = _product_service([p1, p2])

        with pytest.raises(ProductAlreadyExists):
            svc.update(_ACTOR, p2.id, {"sku": "SKU-1"})

    def test_raises_if_category_not_found(self) -> None:
        product = make_product()
        svc = _product_service([product])

        with pytest.raises(CategoryNotFound):
            svc.update(_ACTOR, product.id, {"category_id": uuid.uuid4()})

    def test_raises_if_brand_not_found(self) -> None:
        product = make_product()
        svc = _product_service([product])

        with pytest.raises(BrandNotFound):
            svc.update(_ACTOR, product.id, {"brand_id": uuid.uuid4()})

    def test_raises_on_integrity_error_update(self) -> None:
        product = make_product()
        svc = _product_service([product])
        svc.repo = IntegrityErrorProductRepository([product])

        with pytest.raises(ProductAlreadyExists):
            svc.update(_ACTOR, product.id, {"name": "New"})


class TestProductServiceDelete:
    def test_soft_deletes(self) -> None:
        product = make_product()
        svc = _product_service([product])

        svc.delete(_ACTOR, product.id)

        assert product.deleted_at is not None

    def test_raises_if_not_found(self) -> None:
        svc = _product_service()

        with pytest.raises(ProductNotFound):
            svc.delete(_ACTOR, uuid.uuid4())


# ---------------------------------------------------------------------------
# VariantService
# ---------------------------------------------------------------------------


class TestVariantServiceCreate:
    def test_creates_variant(self) -> None:
        product = make_product()
        svc = _variant_service(products=[product])

        result = svc.create(_ACTOR, product_id=product.id, sku="VAR-1", price="5.00")

        assert result.sku == "VAR-1"

    def test_raises_if_product_not_found(self) -> None:
        svc = _variant_service()

        with pytest.raises(ProductNotFound):
            svc.create(_ACTOR, product_id=uuid.uuid4(), sku="VAR-1", price="5.00")

    def test_raises_if_sku_exists(self) -> None:
        product = make_product()
        existing = make_variant(sku="VAR-1", product_id=product.id)
        svc = _variant_service(variants=[existing], products=[product])

        with pytest.raises(VariantAlreadyExists):
            svc.create(_ACTOR, product_id=product.id, sku="VAR-1", price="5.00")

    def test_raises_on_integrity_error_create(self) -> None:
        product = make_product()
        svc = _variant_service(products=[product])
        svc.repo = IntegrityErrorVariantRepository()

        with pytest.raises(VariantAlreadyExists):
            svc.create(_ACTOR, product_id=product.id, sku="VAR-1", price="5.00")

    def test_raises_on_invalid_attributes(self) -> None:
        category = make_category()
        product = make_product(category_id=category.id)
        attr = make_category_attribute(
            category_id=category.id, key="color", value_type="string", required=True
        )
        svc = _variant_service(
            products=[product], categories=[category], attributes=[attr]
        )

        with pytest.raises(InvalidVariantAttributes):
            svc.create(
                _ACTOR, product_id=product.id, sku="VAR-1", price="5.00", attributes={}
            )

    def test_valid_attributes_pass_validation(self) -> None:
        category = make_category()
        product = make_product(category_id=category.id)
        attr = make_category_attribute(
            category_id=category.id, key="color", value_type="string", required=True
        )
        svc = _variant_service(
            products=[product], categories=[category], attributes=[attr]
        )

        result = svc.create(
            _ACTOR,
            product_id=product.id,
            sku="VAR-1",
            price="5.00",
            attributes={"color": "red"},
        )

        assert result.attributes["color"] == "red"


class TestVariantServiceGet:
    def test_returns_variant(self) -> None:
        variant = make_variant()
        svc = _variant_service(variants=[variant])

        assert svc.get(variant.id).id == variant.id

    def test_raises_if_not_found(self) -> None:
        svc = _variant_service()

        with pytest.raises(VariantNotFound):
            svc.get(uuid.uuid4())


class TestVariantServiceUpdate:
    def test_updates_price(self) -> None:
        variant = make_variant(price="5.00")
        svc = _variant_service(variants=[variant])

        result = svc.update(_ACTOR, variant.id, {"price": "9.99"})

        assert result.price == "9.99"

    def test_raises_if_not_found(self) -> None:
        svc = _variant_service()

        with pytest.raises(VariantNotFound):
            svc.update(_ACTOR, uuid.uuid4(), {"price": "1.00"})

    def test_raises_if_sku_already_exists(self) -> None:
        v1 = make_variant(sku="VAR-1")
        v2 = make_variant(sku="VAR-2")
        svc = _variant_service(variants=[v1, v2])

        with pytest.raises(VariantAlreadyExists):
            svc.update(_ACTOR, v2.id, {"sku": "VAR-1"})

    def test_raises_on_integrity_error_update(self) -> None:
        variant = make_variant()
        svc = _variant_service(variants=[variant])
        svc.repo = IntegrityErrorVariantRepository([variant])

        with pytest.raises(VariantAlreadyExists):
            svc.update(_ACTOR, variant.id, {"price": "1.00"})

    def test_updates_attributes(self) -> None:
        category = make_category()
        product = make_product(category_id=category.id)
        attr = make_category_attribute(
            category_id=category.id, key="color", value_type="string", required=True
        )
        variant = make_variant(product_id=product.id, attributes={"color": "red"})
        svc = _variant_service(
            variants=[variant], products=[product], categories=[category], attributes=[attr]
        )

        result = svc.update(_ACTOR, variant.id, {"attributes": {"color": "blue"}})

        assert result.attributes["color"] == "blue"

    def test_raises_if_updated_attributes_invalid(self) -> None:
        category = make_category()
        product = make_product(category_id=category.id)
        attr = make_category_attribute(
            category_id=category.id, key="color", value_type="string", required=True
        )
        variant = make_variant(product_id=product.id, attributes={"color": "red"})
        svc = _variant_service(
            variants=[variant], products=[product], categories=[category], attributes=[attr]
        )

        with pytest.raises(InvalidVariantAttributes):
            svc.update(_ACTOR, variant.id, {"attributes": {"color": 123}})


class TestVariantServiceDelete:
    def test_soft_deletes(self) -> None:
        variant = make_variant()
        svc = _variant_service(variants=[variant])

        svc.delete(_ACTOR, variant.id)

        assert variant.deleted_at is not None

    def test_raises_if_not_found(self) -> None:
        svc = _variant_service()

        with pytest.raises(VariantNotFound):
            svc.delete(_ACTOR, uuid.uuid4())


# ---------------------------------------------------------------------------
# CategoryAttributeService
# ---------------------------------------------------------------------------


class TestVariantServiceListByProduct:
    def test_raises_if_product_not_found(self) -> None:
        svc = _variant_service()

        with pytest.raises(ProductNotFound):
            svc.list_by_product(uuid.uuid4())


class TestCategoryServiceListByParent:
    def test_raises_if_parent_not_found(self) -> None:
        svc = _category_service()

        with pytest.raises(CategoryNotFound):
            svc.list_by_parent(uuid.uuid4())


class TestProductServiceListByCategory:
    def test_raises_if_category_not_found(self) -> None:
        svc = _product_service()

        with pytest.raises(CategoryNotFound):
            svc.list_by_category(uuid.uuid4())


class TestProductServiceListByBrand:
    def test_raises_if_brand_not_found(self) -> None:
        svc = _product_service()

        with pytest.raises(BrandNotFound):
            svc.list_by_brand(uuid.uuid4())


class TestCategoryAttributeServiceCreate:
    def test_creates_attribute(self) -> None:
        category = make_category()
        svc = _attribute_service(categories=[category])

        result = svc.create(
            _ACTOR, category_id=category.id, key="color", value_type="string"
        )

        assert result.key == "color"

    def test_raises_if_category_not_found(self) -> None:
        svc = _attribute_service()

        with pytest.raises(CategoryNotFound):
            svc.create(
                _ACTOR, category_id=uuid.uuid4(), key="color", value_type="string"
            )

    def test_raises_if_key_already_exists(self) -> None:
        category = make_category()
        existing = make_category_attribute(category_id=category.id, key="color")
        svc = _attribute_service(attributes=[existing], categories=[category])

        with pytest.raises(CategoryAttributeAlreadyExists):
            svc.create(
                _ACTOR, category_id=category.id, key="color", value_type="string"
            )

    def test_raises_on_integrity_error_create(self) -> None:
        category = make_category()
        svc = _attribute_service(categories=[category])
        svc.repo = IntegrityErrorAttributeRepository()

        with pytest.raises(CategoryAttributeAlreadyExists):
            svc.create(
                _ACTOR, category_id=category.id, key="color", value_type="string"
            )


class TestCategoryAttributeServiceGet:
    def test_returns_attribute(self) -> None:
        attr = make_category_attribute()
        svc = _attribute_service(attributes=[attr])

        assert svc.get(attr.id).id == attr.id

    def test_raises_if_not_found(self) -> None:
        svc = _attribute_service()

        with pytest.raises(CategoryAttributeNotFound):
            svc.get(uuid.uuid4())


class TestCategoryAttributeServiceUpdate:
    def test_updates_key(self) -> None:
        attr = make_category_attribute(key="color")
        svc = _attribute_service(attributes=[attr])

        result = svc.update(_ACTOR, attr.id, {"key": "size"})

        assert result.key == "size"

    def test_raises_if_not_found(self) -> None:
        svc = _attribute_service()

        with pytest.raises(CategoryAttributeNotFound):
            svc.update(_ACTOR, uuid.uuid4(), {"key": "size"})

    def test_raises_if_key_already_exists(self) -> None:
        category = make_category()
        attr1 = make_category_attribute(category_id=category.id, key="color")
        attr2 = make_category_attribute(category_id=category.id, key="size")
        svc = _attribute_service(attributes=[attr1, attr2], categories=[category])

        with pytest.raises(CategoryAttributeAlreadyExists):
            svc.update(_ACTOR, attr2.id, {"key": "color"})

    def test_raises_on_integrity_error_update(self) -> None:
        attr = make_category_attribute(key="color")
        svc = _attribute_service(attributes=[attr])
        svc.repo = IntegrityErrorAttributeRepository([attr])

        with pytest.raises(CategoryAttributeAlreadyExists):
            svc.update(_ACTOR, attr.id, {"key": "size"})


class TestCategoryAttributeServiceListByCategory:
    def test_raises_if_category_not_found(self) -> None:
        svc = _attribute_service()

        with pytest.raises(CategoryNotFound):
            svc.list_by_category(uuid.uuid4())


class TestCategoryAttributeServiceDelete:
    def test_hard_deletes(self) -> None:
        attr = make_category_attribute()
        repo = FakeCategoryAttributeRepository([attr])
        svc = CategoryAttributeService.__new__(CategoryAttributeService)
        svc.repo = repo
        svc._category_repo = FakeCategoryRepository()
        svc._audit = FakeAuditPort()
        svc._broker = NoOpMessageBroker()

        svc.delete(_ACTOR, attr.id)

        assert repo.get_by_id(attr.id) is None

    def test_raises_if_not_found(self) -> None:
        svc = _attribute_service()

        with pytest.raises(CategoryAttributeNotFound):
            svc.delete(_ACTOR, uuid.uuid4())
