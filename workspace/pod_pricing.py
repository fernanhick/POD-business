"""
pod_pricing.py -- Regional pricing engine for Printify (US) and Printful (EU)

Implements margin-based pricing profiles, VAT handling, rounding rules, and
auditability for multi-region POD operations.
"""

from dataclasses import dataclass
from typing import Literal
from decimal import Decimal, ROUND_HALF_UP
import json


# ── Pricing Profile Definitions ──────────────────────────────────

@dataclass
class PricingProfile:
    """Definition of a regional pricing profile."""
    name: str  # e.g., "US_PRINTIFY"
    market: Literal["US", "EU"]
    provider: Literal["printify", "printful"]
    margin_target: Decimal  # e.g., 0.35 for 35%
    marketplace_fee_buffer: Decimal  # e.g., 0.06 for 6%
    vat_buffer: Decimal  # e.g., 0.22 for 22% VAT (EU only)
    rounding_rule: Literal["cents_99", "cents_95"]  # USD .99, EUR .95
    currency: str  # "USD" or "EUR"
    description: str


# US Pricing Profile (Printify)
US_PRINTIFY = PricingProfile(
    name="US_PRINTIFY",
    market="US",
    provider="printify",
    margin_target=Decimal("0.35"),  # 35% contribution
    marketplace_fee_buffer=Decimal("0.06"),  # 6% Etsy + fluctuations
    vat_buffer=Decimal("0.00"),  # No VAT in US
    rounding_rule="cents_99",  # $X.99
    currency="USD",
    description="Accessible US pricing via Printify for US-based Etsy channel",
)

# EU Pricing Profiles (Printful) - by country VAT bucket
EU_STANDARD_21 = PricingProfile(
    name="EU_STANDARD_21",
    market="EU",
    provider="printful",
    margin_target=Decimal("0.30"),  # 30% contribution
    marketplace_fee_buffer=Decimal("0.07"),  # 7% Etsy + fees
    vat_buffer=Decimal("0.21"),  # 21% standard VAT (fallback)
    rounding_rule="cents_95",  # €X.95
    currency="EUR",
    description="EU pricing (pan-EU, fallback VAT 21%)",
)

EU_LOW_19 = PricingProfile(
    name="EU_LOW_19",
    market="EU",
    provider="printful",
    margin_target=Decimal("0.30"),
    marketplace_fee_buffer=Decimal("0.07"),
    vat_buffer=Decimal("0.19"),
    rounding_rule="cents_95",
    currency="EUR",
    description="EU pricing for Germany-like markets (19% VAT)",
)

EU_MID_20 = PricingProfile(
    name="EU_MID_20",
    market="EU",
    provider="printful",
    margin_target=Decimal("0.30"),
    marketplace_fee_buffer=Decimal("0.07"),
    vat_buffer=Decimal("0.20"),
    rounding_rule="cents_95",
    currency="EUR",
    description="EU pricing for France/Austria-like markets (20% VAT)",
)

EU_HIGH_22 = PricingProfile(
    name="EU_HIGH_22",
    market="EU",
    provider="printful",
    margin_target=Decimal("0.30"),
    marketplace_fee_buffer=Decimal("0.07"),
    vat_buffer=Decimal("0.22"),
    rounding_rule="cents_95",
    currency="EUR",
    description="EU pricing for Italy/Slovenia/Romania-like markets (22% VAT)",
)

EU_HIGH_23 = PricingProfile(
    name="EU_HIGH_23",
    market="EU",
    provider="printful",
    margin_target=Decimal("0.30"),
    marketplace_fee_buffer=Decimal("0.07"),
    vat_buffer=Decimal("0.23"),
    rounding_rule="cents_95",
    currency="EUR",
    description="EU pricing for high-VAT markets (23% VAT)",
)

# Profile registry
PROFILES = {
    "US_PRINTIFY": US_PRINTIFY,
    "EU_STANDARD_21": EU_STANDARD_21,
    "EU_LOW_19": EU_LOW_19,
    "EU_MID_20": EU_MID_20,
    "EU_HIGH_22": EU_HIGH_22,
    "EU_HIGH_23": EU_HIGH_23,
}

# Country to VAT bucket mapping
COUNTRY_TO_VAT_BUCKET = {
    "DE": "EU_LOW_19",
    "FR": "EU_MID_20",
    "AT": "EU_MID_20",
    "BG": "EU_MID_20",
    "IT": "EU_HIGH_22",
    "SI": "EU_HIGH_22",
    "RO": "EU_HIGH_22",
    "IE": "EU_HIGH_23",
    "PL": "EU_HIGH_23",
    "PT": "EU_HIGH_23",
    "GR": "EU_HIGH_23",
    "FI": "EU_HIGH_23",
}


# ── Pricing Functions ──────────────────────────────────────────

def get_profile_for_provider_market(
    provider: Literal["printify", "printful"],
    market: Literal["US", "EU"],
    country: str | None = None,
) -> PricingProfile:
    """
    Return the appropriate pricing profile for a provider/market combo.
    
    For EU with known country, use country-specific VAT bucket; else EU_STANDARD_21.
    """
    if provider == "printify" and market == "US":
        return US_PRINTIFY
    elif provider == "printful" and market == "EU":
        if country and country in COUNTRY_TO_VAT_BUCKET:
            profile_name = COUNTRY_TO_VAT_BUCKET[country]
            return PROFILES[profile_name]
        return EU_STANDARD_21
    else:
        raise ValueError(f"Unsupported provider/market: {provider}/{market}")


def calc_price_cents(
    base_cost_cents: int,
    shipping_cents: int,
    profile: PricingProfile,
    size_tier: str | None = None,
    oversize_costs_cents: dict[str, int] | None = None,
) -> tuple[int, dict]:
    """
    Calculate final product price in cents using profile formula.
    
    Formula: price = (base + shipping + size_delta) * (1 + fee_buffer + vat_buffer) / (1 - margin_target)
    Then apply rounding rule.
    
    Returns: (final_price_cents, debug_info_dict)
    """
    # Determine actual cost for this size
    cost = base_cost_cents
    if size_tier and oversize_costs_cents and size_tier in oversize_costs_cents:
        cost = oversize_costs_cents[size_tier]
    
    # Add shipping
    total_cost = cost + shipping_cents
    
    # Apply buffers and margin
    multiplier = Decimal(1) + profile.marketplace_fee_buffer + profile.vat_buffer
    divisor = Decimal(1) - profile.margin_target
    raw_price = (Decimal(total_cost) * multiplier) / divisor
    
    # Round per profile rule
    if profile.rounding_rule == "cents_99":
        # USD: round up to next dollar, then .99
        dollars = int(raw_price / 100)
        if raw_price % 100 > 0:
            dollars += 1
        final_price_cents = dollars * 100 - 1
    else:  # cents_95
        # EUR: round to nearest euros.95
        euros = int(raw_price / 100)
        remainder = raw_price % 100
        if remainder > 95:
            euros += 1
        final_price_cents = euros * 100 + 95
    
    debug_info = {
        "base_cost_cents": base_cost_cents,
        "shipping_cents": shipping_cents,
        "size_tier": size_tier,
        "cost_after_size_cents": cost,
        "total_cost_cents": total_cost,
        "raw_price_decimal": str(raw_price),
        "final_price_cents": final_price_cents,
        "final_price_dollars": f"{final_price_cents / 100:.2f}",
        "profile_name": profile.name,
        "margin_target": str(profile.margin_target),
        "fee_buffer": str(profile.marketplace_fee_buffer),
        "vat_buffer": str(profile.vat_buffer),
    }
    
    return int(final_price_cents), debug_info


def calc_variant_prices(
    base_cost_cents: int,
    shipping_cents: int,
    profile: PricingProfile,
    oversize_costs_cents: dict[str, int] | None = None,
    variant_sizes: list[str] | None = None,
) -> list[dict]:
    """
    Calculate prices for all variant sizes.
    
    Returns list of {size, price_cents, price_display, debug_info}.
    """
    if not variant_sizes:
        variant_sizes = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL"]
    
    results = []
    for size in variant_sizes:
        price_cents, debug = calc_price_cents(
            base_cost_cents,
            shipping_cents,
            profile,
            size_tier=size,
            oversize_costs_cents=oversize_costs_cents,
        )
        results.append({
            "size": size,
            "price_cents": price_cents,
            "price_display": f"{price_cents / 100:.2f} {profile.currency}",
            "debug_info": debug,
        })
    
    return results


# ── Snapshot Tests (Reference Data for Verification) ──────────────

def generate_price_snapshots() -> dict:
    """
    Generate representative price snapshots for verification.
    
    Tests sizes S, XL, 2XL, 4XL/5XL across both profiles.
    """
    # Printify T-Shirt (SwiftPOD, blueprint 12)
    printify_tshirt_base = 1129  # cents = $11.29
    printify_tshirt_shipping = 429  # cents = $4.29
    printify_tshirt_oversize = {
        "2XL": 1382,
        "3XL": 1612,
        "4XL": 1863,
    }
    
    # Printful T-Shirt (placeholder; adjust when Printful integration defined)
    printful_tshirt_base = 1200  # cents = $12.00 (example)
    printful_tshirt_shipping = 500  # cents = €5.00 (example)
    printful_tshirt_oversize = {
        "2XL": 1450,
        "3XL": 1650,
        "4XL": 1900,
    }
    
    snapshots = {
        "US_PRINTIFY_TSHIRT": {
            "profile": "US_PRINTIFY",
            "product": "T-Shirt",
            "base_cost_cents": printify_tshirt_base,
            "shipping_cents": printify_tshirt_shipping,
            "oversize_costs_cents": printify_tshirt_oversize,
            "prices": calc_variant_prices(
                printify_tshirt_base,
                printify_tshirt_shipping,
                US_PRINTIFY,
                oversize_costs_cents=printify_tshirt_oversize,
                variant_sizes=["S", "XL", "2XL", "4XL"],
            ),
        },
        "EU_STANDARD_TSHIRT": {
            "profile": "EU_STANDARD_21",
            "product": "T-Shirt",
            "base_cost_cents": printful_tshirt_base,
            "shipping_cents": printful_tshirt_shipping,
            "oversize_costs_cents": printful_tshirt_oversize,
            "prices": calc_variant_prices(
                printful_tshirt_base,
                printful_tshirt_shipping,
                EU_STANDARD_21,
                oversize_costs_cents=printful_tshirt_oversize,
                variant_sizes=["S", "XL", "2XL", "4XL"],
            ),
        },
    }
    
    return snapshots


def print_snapshots():
    """Print representative price snapshots for manual verification."""
    snapshots = generate_price_snapshots()
    print("\n=== PRICING SNAPSHOTS (FOR VERIFICATION) ===\n")
    for snapshot_name, snapshot_data in snapshots.items():
        print(f"{snapshot_name}:")
        print(f"  Profile: {snapshot_data['profile']}")
        print(f"  Product: {snapshot_data['product']}")
        print(f"  Base cost: ${snapshot_data['base_cost_cents'] / 100:.2f}")
        print(f"  Shipping: ${snapshot_data['shipping_cents'] / 100:.2f}")
        print(f"  Prices:")
        for variant in snapshot_data['prices']:
            print(f"    {variant['size']}: {variant['price_display']}")
        print()


if __name__ == "__main__":
    # Print snapshots for manual review
    print_snapshots()
    
    # Verify profiles are defined
    print("=== AVAILABLE PROFILES ===")
    for name, profile in PROFILES.items():
        print(f"  {name}: {profile.description}")
    
    print("\n=== COUNTRY TO VAT BUCKET MAPPING ===")
    for country, bucket in COUNTRY_TO_VAT_BUCKET.items():
        print(f"  {country} -> {bucket}")
