import pytest
import httpx
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.main import create_app
from app.services.auth import token_digest
from app.services.vault import VaultService


class FakeVaultStore:
    def __init__(self):
        self.profile = None
        self.addresses = {}
        self.products = {}

    def seed_demo_address(self, record):
        self.addresses.setdefault(record["id"], record)

    def get_profile(self):
        return self.profile

    def save_profile(self, record):
        self.profile = record

    def list_addresses(self):
        return list(self.addresses.values())

    def get_address(self, id):
        return self.addresses.get(id)

    def save_address(self, record):
        self.addresses[record["id"]] = record

    def list_products(self):
        return list(self.products.values())

    def get_product(self, id):
        return self.products.get(id)

    def save_product(self, record):
        self.products[record["id"]] = record


def service():
    return VaultService(FakeVaultStore())


def test_seed_address_once_and_persist_new_address():
    store = FakeVaultStore()
    first = VaultService(store)
    first.seed_demo_address()
    first.seed_demo_address()
    assert len(first.list_addresses()) == 1
    saved = first.create_address({
        "label": "Demo flat", "line1": " 10 Fiction Street ", "city": " Pune ",
        "region": "Maharashtra", "postalCode": "411001", "country": "India",
    })
    again = VaultService(store)
    assert len(again.list_addresses()) == 2
    assert again.get_address(saved["id"])["line1"] == "10 Fiction Street"
    assert saved["isDemo"] is False


def test_profile_save_read_and_required_trimmed_fields():
    vault = service()
    profile = vault.save_profile({"name": " Demo User ", "phone": " 9999999999 ",
                                  "email": " demo@example.test "})
    assert profile["name"] == "Demo User"
    assert vault.get_profile()["phone"] == "9999999999"
    with pytest.raises(ValueError):
        vault.save_profile({"name": "   ", "phone": "9999999999", "email": "demo@example.test"})


def test_product_requires_category_brand_pair_but_no_serial_number():
    vault = service()
    category = vault.catalog()["categories"][0]
    brand = category["brands"][0]
    product = vault.create_product({"categoryId": category["id"], "brandId": brand["id"],
                                    "displayName": " Example Model "})
    assert product["displayName"] == "Example Model"
    assert "serialNumber" not in product
    assert vault.get_product(product["id"])["id"] == product["id"]
    with pytest.raises(ValueError):
        vault.create_product({"categoryId": category["id"], "brandId": "not-a-brand",
                              "displayName": "Example Model"})
    with pytest.raises(LookupError):
        vault.get_product("missing-id")


def test_product_and_address_edit_keep_ids():
    vault = service()
    vault.seed_demo_address()
    address = vault.create_address({"label": "Home", "line1": "1 Sample Lane",
                                     "city": "Pune", "region": "Maharashtra", "postalCode": "411001",
                                     "country": "India"})
    updated_address = vault.update_address(address["id"], {"label": "Office"})
    assert updated_address["id"] == address["id"]
    category = vault.catalog()["categories"][0]
    product = vault.create_product({"categoryId": category["id"],
                                    "brandId": category["brands"][0]["id"],
                                    "displayName": "Example"})
    updated_product = vault.update_product(product["id"], {"displayName": "New Example"})
    assert updated_product["id"] == product["id"]


def test_catalog_contains_agreed_breadth_without_agent_coverage_claim():
    categories = service().catalog()["categories"]
    assert 10 <= len(categories) <= 15
    assert all(10 <= len(category["brands"]) <= 15 for category in categories)


@pytest.mark.asyncio
async def test_authenticated_vault_routes_share_saved_address():
    class Sessions:
        def get(self, digest):
            if digest == token_digest("fictional-token"):
                return {"expires_at": datetime.now(timezone.utc) + timedelta(hours=1), "revoked": False}
            return None

    app = create_app(settings=Settings(), session_store=Sessions(), vault_store=FakeVaultStore())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://api.test") as client:
        assert (await client.get("/api/catalog")).status_code == 401
        client.cookies.set("__session", "fictional-token")
        created = await client.post("/api/addresses", json={
            "label": "Home", "line1": "1 Sample Lane", "city": "Pune",
            "region": "Maharashtra", "postalCode": "411001", "country": "India",
        })
        assert created.status_code == 200
        addresses = (await client.get("/api/addresses")).json()
        assert created.json()["id"] in {row["id"] for row in addresses}
