import unittest

from cloud_core.app.business_math import (
    calculate_offer_economics,
)


class OfferEconomicsTests(unittest.TestCase):

    def test_simple_offer_without_fees(self):
        result = calculate_offer_economics(
            asking_price=55,
            offer_price=42,
            item_cost=31,
        )

        self.assertEqual(
            result.net_profit,
            result.net_profit.__class__("11.00"),
        )

        self.assertEqual(
            result.net_margin_percent,
            result.net_margin_percent.__class__("26.19"),
        )

        self.assertEqual(
            result.discount_from_asking_percent,
            result.discount_from_asking_percent.__class__("23.64"),
        )

        self.assertEqual(
            result.break_even_price,
            result.break_even_price.__class__("31.00"),
        )

    def test_platform_fee_is_deterministic(self):
        result = calculate_offer_economics(
            asking_price=55,
            offer_price=42,
            item_cost=20,
            seller_shipping_cost=5,
            other_costs=1,
            platform_fee_rate_percent=10,
            platform_fixed_fee=0.30,
        )

        self.assertEqual(
            result.platform_fee,
            result.platform_fee.__class__("4.50"),
        )

        self.assertEqual(
            result.total_cost,
            result.total_cost.__class__("30.50"),
        )

        self.assertEqual(
            result.net_profit,
            result.net_profit.__class__("11.50"),
        )

    def test_negative_cost_rejected(self):
        with self.assertRaises(ValueError):
            calculate_offer_economics(
                asking_price=55,
                offer_price=42,
                item_cost=-1,
            )


if __name__ == "__main__":
    unittest.main()
