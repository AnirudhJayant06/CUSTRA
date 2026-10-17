"""Validation and storage of shared demo profile, addresses and products."""

import calendar
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from app.models.account import AddressInput, ProfileInput
from app.models.product import ProductInput


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class VaultService:
    def __init__(self, store):
        self.store = store

    def catalog(self) -> dict:
        catalog = json.loads((DATA_DIR / "catalog.json").read_text())
        catalog['models'] = json.loads((DATA_DIR / 'product_models.json').read_text())['models']
        return catalog

    def service_centers(self) -> dict:
        return json.loads((DATA_DIR / "service_centers.json").read_text())

    def seed_demo_address(self) -> None:
        self.store.seed_demo_address({
            "id": "demo-address", "label": "Demo address", "line1": "10 Fiction Street",
            "line2": "", "city": "Pune", "region": "Maharashtra", "postalCode": "411001",
            "country": "India", "isDemo": True, "createdAt": timestamp(),
        })

    def get_profile(self) -> dict:
        return self.store.get_profile() or {"name": "", "phone": "", "email": "", "defaultAddressId": "demo-address"}

    def save_profile(self, payload: dict) -> dict:
        profile = ProfileInput.model_validate(payload).model_dump()
        previous = self.store.get_profile() or {}
        profile.update({"defaultAddressId": previous.get("defaultAddressId", "demo-address"),
                        "updatedAt": timestamp()})
        self.store.save_profile(profile)
        return profile

    def set_default_address(self, address_id: str) -> dict:
        self.seed_demo_address()
        self.get_address(address_id)
        profile = self.get_profile()
        profile.update(defaultAddressId=address_id, updatedAt=timestamp())
        self.store.save_profile(profile)
        return profile

    def list_addresses(self) -> list[dict]:
        self.seed_demo_address()
        return self.store.list_addresses()

    def get_address(self, id: str) -> dict:
        result = self.store.get_address(id)
        if not result:
            raise LookupError("Address not found")
        return result

    def create_address(self, payload: dict) -> dict:
        record = AddressInput.model_validate(payload).model_dump()
        record.update({"id": uuid.uuid4().hex, "isDemo": False, "createdAt": timestamp()})
        self.store.save_address(record)
        return record

    def update_address(self, id: str, changes: dict) -> dict:
        existing = self.get_address(id)
        if existing.get("isDemo"):
            raise ValueError("Demo address cannot be edited")
        data = {key: existing[key] for key in AddressInput.model_fields}
        data.update(changes)
        record = AddressInput.model_validate(data).model_dump()
        record.update({"id": id, "isDemo": False, "createdAt": existing["createdAt"],
                       "updatedAt": timestamp()})
        self.store.save_address(record)
        return record

    def list_products(self) -> list[dict]:
        return [record for record in self.store.list_products() if not record.get('deletedAt')]

    def get_product(self, id: str) -> dict:
        result = self.store.get_product(id)
        if not result or result.get('deletedAt'):
            raise LookupError("Product not found")
        return result

    def _validate_product(self, payload: dict) -> dict:
        product = ProductInput.model_validate(payload).model_dump(mode="json")
        category = next((x for x in self.catalog()["categories"] if x["id"] == product["categoryId"]), None)
        if not category or product["brandId"] not in {x["id"] for x in category["brands"]}:
            raise ValueError("Choose a brand from the selected category")
        product['modelNumber'] = product['modelNumber'] or None
        brand = next(x for x in category['brands'] if x['id'] == product['brandId'])
        if product['nickname'] is not None:
            product['displayName'] = product['nickname'] or f"{brand['name']} {category['name']}"
        elif not product['displayName']:
            product['displayName'] = f"{brand['name']} {category['name']}"
        if product['purchaseDate'] and product['warrantyMonths']:
            start = date.fromisoformat(product['purchaseDate'])
            months = start.year * 12 + start.month - 1 + product['warrantyMonths']
            year, month = divmod(months, 12)
            month += 1
            product['warrantyExpiry'] = date(year, month, min(start.day, calendar.monthrange(year, month)[1])).isoformat()
        return product

    def create_product(self, payload: dict) -> dict:
        record = self._validate_product(payload)
        record.update({"id": uuid.uuid4().hex, "createdAt": timestamp()})
        self.store.save_product(record)
        return record

    def update_product(self, id: str, changes: dict) -> dict:
        existing = self.get_product(id)
        data = {key: existing.get(key) for key in ProductInput.model_fields}
        data.update(changes)
        if any(key in changes and changes[key] != existing.get(key) for key in ('categoryId', 'brandId')) and 'modelNumber' not in changes:
            data['modelNumber'] = None
        if 'displayName' in changes and 'nickname' not in changes:
            data['nickname'] = None
        if ('purchaseDate' in changes or 'warrantyMonths' in changes) and existing.get('warrantyMonths'):
            data['warrantyExpiry'] = None
        record = self._validate_product(data)
        record.update({"id": id, "createdAt": existing["createdAt"], "updatedAt": timestamp()})
        self.store.save_product(record)
        return record
