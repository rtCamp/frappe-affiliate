# Copyright (c) 2025, rtCamp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CouponBatch(Document):
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
                "pricing_rule": self.pricing_rule,
                "custom_recurring_pricing_rule": self.recurring_pricing_rule,
                "valid_from": self.valid_from,
                "valid_upto": self.valid_upto,
                "maximum_use": self.maximum_use,
                "custom_coupon_batch": self.name,
                "custom_subscription_maximum_use": self.subscription_maximum_use,
                "custom_maximum_user_use_count": self.maximum_user_use_count,
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
            coupon.custom_pricing_rule = self.pricing_rule
            coupon.custom_recurring_pricing_rule = self.recurring_pricing_rule
            coupon.custom_subscription_maximum_use = self.subscription_maximum_use
            coupon.valid_from = self.valid_from
            coupon.valid_upto = self.valid_upto
            coupon.maximum_use = self.maximum_use
            coupon.save()
