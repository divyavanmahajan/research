"""Map YAML attribute types and field name heuristics to Faker providers."""

from __future__ import annotations

import random
import uuid as uuid_mod
from typing import Any

from faker import Faker

# Field name fragments that trigger specific Faker providers
_NAME_HINTS: list[tuple[list[str], str]] = [
    (["email"], "email"),
    (["full_name", "name"], "name"),
    (["phone", "tel"], "phone_number"),
    (["city"], "city"),
    (["country"], "country_code"),
    (["address", "street"], "street_address"),
    (["company", "vendor", "org_name"], "company"),
    (["code", "cost_center"], "bothify"),
    (["url", "website"], "url"),
    (["description", "notes", "comment"], "sentence"),
    (["status"], None),  # handled by enum
]


def generate_value(
    attr_name: str,
    attr_type: str,
    enum: list[str],
    nullable: bool,
    fake: Faker,
    rng: random.Random,
) -> Any:
    """Generate a single fake value for an attribute."""
    # Nullable fields: ~20% chance of None
    if nullable and rng.random() < 0.2:
        return None

    # Enum always wins if present
    if enum:
        return rng.choice(enum)

    return _generate_by_type_and_name(attr_name, attr_type, fake, rng)


def _generate_by_type_and_name(
    attr_name: str,
    attr_type: str,
    fake: Faker,
    rng: random.Random,
) -> Any:
    lower = attr_name.lower()

    if attr_type == "uuid":
        return fake.uuid4()

    if attr_type == "boolean":
        return rng.choice([True, False])

    if attr_type == "integer":
        if "level" in lower or "maturity" in lower:
            return rng.randint(1, 5)
        return rng.randint(1, 10000)

    if attr_type == "float":
        return round(rng.uniform(0, 10000), 2)

    if attr_type == "date":
        return fake.date_between(start_date="-5y", end_date="today").isoformat()

    if attr_type == "timestamp":
        return fake.date_time_between(start_date="-5y", end_date="now").isoformat()

    # string — use name heuristics
    for fragments, provider in _NAME_HINTS:
        if any(frag in lower for frag in fragments):
            if provider == "email":
                return fake.company_email()
            if provider == "name":
                return fake.name()
            if provider == "phone_number":
                return fake.phone_number()[:20]
            if provider == "city":
                return fake.city()
            if provider == "country_code":
                return fake.country_code()
            if provider == "street_address":
                return fake.street_address()
            if provider == "company":
                return fake.company()
            if provider == "bothify":
                return fake.bothify(text="??-####").upper()
            if provider == "url":
                return fake.url()
            if provider == "sentence":
                return fake.sentence()

    # Default string fallback
    if "id" in lower and not lower.endswith("_id"):
        return fake.bothify(text="ID-######")

    return fake.word().capitalize()
