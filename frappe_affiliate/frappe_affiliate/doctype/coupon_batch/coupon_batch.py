# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CouponBatch(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from erpnext.accounts.doctype.pricing_rule_item_code.pricing_rule_item_code import (
            PricingRuleItemCode,
        )
        from frappe.types import DF

        amended_from: DF.Link | None
        apply_except_item_code: DF.Table[PricingRuleItemCode]
        apply_on_item_code: DF.Table[PricingRuleItemCode]
        apply_to_recurring: DF.Check
        code_length: DF.Int
        coupon_code: DF.Data | None
        coupon_name: DF.Data
        coupon_type: DF.Literal["Single", "Batch of Random Coupon Codes"]  # noqa F722
        coupons_count: DF.Int
        customer: DF.Link | None
        description: DF.TextEditor | None
        disable: DF.Check
        discount: DF.Float
        maximum_use: DF.Int
        maximum_user_use_count: DF.Int
        prefix: DF.Data | None
        rate_or_discount: DF.Literal["Percentage", "Amount"]  # noqa 821
        recurring_discount: DF.Float
        recurring_rate_or_discount: DF.Literal["Percentage", "Amount"]  # noqa 821
        sales_partner: DF.Link | None
        subscription_maximum_use: DF.Int
        valid_from: DF.Date | None
        valid_upto: DF.Date | None
    # end: auto-generated types

    def validate(self):
        if not frappe.flags.in_migration:
            if self.coupon_type == "Single" and not self.coupon_code:
                self.coupon_code = frappe.generate_hash()[:10].upper()

    def on_update(self):
        if not frappe.flags.in_migration:
            if frappe.db.exists("Coupon Code", {"custom_coupon_batch": self.name}):
                self.update_coupons()
            else:
                self.generate_coupons()

    def generate_coupons(self):
        coupon_type = self.coupon_type
        if coupon_type == "Single":
            self.generate_single_coupon()
        else:
            self.generate_batch_coupons()

    def generate_single_coupon(self):
        self.generate_coupon(self.coupon_name, self.coupon_code)

    def generate_coupon(self, coupon_name, coupon_code):
        coupon = frappe.get_doc(
            {
                "doctype": "Coupon Code",
                "coupon_name": coupon_name,
                "coupon_code": coupon_code,
                "custom_sales_partner": self.sales_partner,
                "coupon_type": "Promotional",
                "custom_apply_to_recurring": self.apply_to_recurring,
                "valid_from": self.valid_from,
                "valid_upto": self.valid_upto,
                "maximum_use": self.maximum_use,
                "custom_coupon_batch": self.name,
                "custom_subscription_maximum_use": self.subscription_maximum_use,
                "custom_maximum_user_use_count": self.maximum_user_use_count,
                "custom_disable": self.disable,
            }
        )
        coupon.save()

    def generate_batch_coupons(self):
        prefix = self.prefix or ""
        for i in range(self.coupons_count):
            self.generate_coupon(
                f"{self.coupon_name} {i+1}",
                f"{prefix}{frappe.generate_hash()[:self.code_length].upper()}",
            )

    def update_coupons(self):
        coupons = frappe.get_all(
            "Coupon Code", filters={"custom_coupon_batch": self.name}, pluck="name"
        )

        for coupon_name in coupons:
            coupon = frappe.get_doc("Coupon Code", coupon_name)
            coupon.custom_apply_to_recurring = self.apply_to_recurring
            coupon.custom_sales_partner = self.sales_partner
            coupon.custom_subscription_maximum_use = self.subscription_maximum_use
            coupon.custom_maximum_user_use_count = self.maximum_user_use_count
            coupon.valid_from = self.valid_from
            coupon.valid_upto = self.valid_upto
            coupon.maximum_use = self.maximum_use
            coupon.custom_disable = self.disable
            coupon.save()
