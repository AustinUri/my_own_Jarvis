from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")
PERCENT = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def percent(value: Decimal) -> Decimal:
    return value.quantize(
        PERCENT,
        rounding=ROUND_HALF_UP,
    )


@dataclass(frozen=True)
class OfferEconomics:
    asking_price: Decimal
    offer_price: Decimal

    item_cost: Decimal
    seller_shipping_cost: Decimal
    other_costs: Decimal

    platform_fee_rate_percent: Decimal
    platform_fixed_fee: Decimal

    platform_fee: Decimal
    total_cost_before_fees: Decimal
    total_cost: Decimal

    net_profit: Decimal
    net_margin_percent: Decimal
    return_on_cost_percent: Decimal
    discount_from_asking_percent: Decimal
    break_even_price: Decimal

    def to_dict(self) -> dict:
        return {
            key: float(value)
            if isinstance(value, Decimal)
            else value
            for key, value in asdict(self).items()
        }


def calculate_offer_economics(
    *,
    asking_price,
    offer_price,
    item_cost,
    seller_shipping_cost=0,
    other_costs=0,
    platform_fee_rate_percent=0,
    platform_fixed_fee=0,
) -> OfferEconomics:

    asking = money(asking_price)
    offer = money(offer_price)
    item = money(item_cost)
    shipping = money(seller_shipping_cost)
    other = money(other_costs)
    fixed_fee = money(platform_fixed_fee)

    fee_rate = Decimal(
        str(platform_fee_rate_percent)
    )

    values = {
        "asking_price": asking,
        "offer_price": offer,
        "item_cost": item,
        "seller_shipping_cost": shipping,
        "other_costs": other,
        "platform_fixed_fee": fixed_fee,
    }

    for name, value in values.items():
        if value < 0:
            raise ValueError(
                f"{name} cannot be negative"
            )

    if asking <= 0:
        raise ValueError(
            "asking_price must be greater than zero"
        )

    if offer <= 0:
        raise ValueError(
            "offer_price must be greater than zero"
        )

    if fee_rate < 0 or fee_rate >= 100:
        raise ValueError(
            "platform_fee_rate_percent must be "
            "between 0 and 100"
        )

    variable_fee = (
        offer * fee_rate / Decimal("100")
    )

    platform_fee = money(
        variable_fee + fixed_fee
    )

    pre_fee_cost = money(
        item + shipping + other
    )

    total_cost = money(
        pre_fee_cost + platform_fee
    )

    net_profit = money(
        offer - total_cost
    )

    net_margin = (
        percent(
            net_profit
            / offer
            * Decimal("100")
        )
        if offer
        else Decimal("0")
    )

    return_on_cost = (
        percent(
            net_profit
            / total_cost
            * Decimal("100")
        )
        if total_cost
        else Decimal("0")
    )

    discount = percent(
        (asking - offer)
        / asking
        * Decimal("100")
    )

    rate_fraction = (
        fee_rate / Decimal("100")
    )

    denominator = (
        Decimal("1") - rate_fraction
    )

    break_even = money(
        (
            pre_fee_cost
            + fixed_fee
        )
        / denominator
    )

    return OfferEconomics(
        asking_price=asking,
        offer_price=offer,
        item_cost=item,
        seller_shipping_cost=shipping,
        other_costs=other,
        platform_fee_rate_percent=fee_rate,
        platform_fixed_fee=fixed_fee,
        platform_fee=platform_fee,
        total_cost_before_fees=pre_fee_cost,
        total_cost=total_cost,
        net_profit=net_profit,
        net_margin_percent=net_margin,
        return_on_cost_percent=return_on_cost,
        discount_from_asking_percent=discount,
        break_even_price=break_even,
    )
