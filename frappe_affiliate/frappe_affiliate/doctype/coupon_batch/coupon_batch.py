# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CouponBatch(Document):
    def validate(self):
        if self.coupon_type == "Single" and not self.coupon_code:
            self.coupon_code = frappe.generate_hash()[:10].upper()

    def on_update(self):
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
        coupon = frappe.get_doc(
            {
                "doctype": "Coupon Code",
                "coupon_name": self.coupon_name,
                "coupon_code": self.coupon_code,
                "custom_sales_partner": self.sales_partner,
                "coupon_type": "Promotional",
                "custom_apply_to_recurring": self.apply_to_recurring,
                "pricing_rule": self.pricing_rule,
                "custom_recurring_pricing_rule": self.recurring_pricing_rule,
                "valid_from": self.valid_from,
                "valid_upto": self.valid_upto,
                "maximum_use": self.maximum_use,
                "custom_coupon_batch": self.name,
            }
        )
        coupon.insert()

    def generate_batch_coupons(self):
        prefix = self.prefix or ""
        prefix_length = len(prefix)
        generate_length = self.code_length - prefix_length
        for i in range(self.coupons_count):
            coupon = frappe.get_doc(
                {
                    "doctype": "Coupon Code",
                    "coupon_name": f"{self.coupon_name} {i+1}",
                    "coupon_code": f"{prefix}{frappe.generate_hash()[:generate_length].upper()}",
                    "custom_sales_partner": self.sales_partner,
                    "coupon_type": "Promotional",
                    "custom_apply_to_recurring": self.apply_to_recurring,
                    "pricing_rule": self.pricing_rule,
                    "custom_recurring_pricing_rule": self.recurring_pricing_rule,
                    "valid_from": self.valid_from,
                    "valid_upto": self.valid_upto,
                    "maximum_use": self.maximum_use,
                    "custom_coupon_batch": self.name,
                }
            )
            coupon.insert()

    def update_coupons(self):
        coupons = frappe.get_all(
            "Coupon Code", filters={"custom_coupon_batch": self.name}, pluck="name"
        )

        for coupon_name in coupons:
            coupon = frappe.get_doc("Coupon Code", coupon_name)
            coupon.custom_apply_to_recurring = self.apply_to_recurring
            coupon.custom_sales_partner = self.sales_partner
            coupon.custom_pricing_rule = self.pricing_rule
            coupon.custom_recurring_pricing_rule = self.recurring_pricing_rule
            coupon.valid_from = self.valid_from
            coupon.valid_upto = self.valid_upto
            coupon.maximum_use = self.maximum_use
            coupon.save()
