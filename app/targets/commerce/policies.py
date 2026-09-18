"""Small immutable commerce fixtures and policy lookup helpers."""

from datetime import date

from .domain_models import Product, PromotionPolicy


PRODUCTS: tuple[Product, ...] = (
    Product(id="P1", name="Running Shoes", price=499, stock=10),
    Product(id="P2", name="Travel Backpack", price=650, stock=4),
    Product(id="P3", name="Coffee Maker", price=799, stock=0),
)

POLICIES: tuple[PromotionPolicy, ...] = (
    PromotionPolicy(
        id="POLICY_A",
        starts_at=date(2026, 1, 1),
        ends_at=date(2026, 1, 31),
        min_amount=500,
        gift="Gift A",
    ),
    PromotionPolicy(
        id="POLICY_B",
        starts_at=date(2026, 2, 1),
        ends_at=date(2026, 2, 28),
        min_amount=600,
        gift="Gift B",
    ),
)


def get_policy(policy_id: str) -> PromotionPolicy:
    normalized_id = policy_id.strip().upper()
    for policy in POLICIES:
        if policy.id == normalized_id:
            return policy
    raise ValueError(f"unknown policy_id: {policy_id}")
