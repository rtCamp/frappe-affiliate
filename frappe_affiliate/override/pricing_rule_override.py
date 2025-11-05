import frappe
from erpnext.accounts.doctype.pricing_rule.pricing_rule import PricingRule
from frappe import _, throw
from frappe.utils import cint

apply_on_dict = {"Item Code": "items", "Item Group": "item_groups", "Brand": "brands"}

other_fields = ["other_item_code", "other_item_group", "other_brand"]


class PricingRuleOverride(PricingRule):
    def validate_mandatory(self):
        if self.has_priority and not self.priority:
            throw(
                _("Priority is mandatory"),
                frappe.MandatoryError,
                _("Please Set Priority"),
            )

        if self.priority and not self.has_priority:
            self.has_priority = 1

        for apply_on, field in apply_on_dict.items():
            if self.apply_on == "Item Code" and field == "items":
                continue
            if self.apply_on == apply_on and len(self.get(field) or []) < 1:
                throw(
                    _("{0} is not added in the table").format(apply_on),
                    frappe.MandatoryError,
                )

        tocheck = frappe.scrub(self.get("applicable_for", ""))
        if tocheck and not self.get(tocheck):
            throw(
                _("{0} is required").format(_(self.meta.get_label(tocheck))),
                frappe.MandatoryError,
            )

        if self.apply_rule_on_other:
            o_field = "other_" + frappe.scrub(self.apply_rule_on_other)
            if not self.get(o_field) and o_field in other_fields:
                frappe.throw(
                    _(
                        "For the 'Apply Rule On Other' condition the field {0} is mandatory"
                    ).format(frappe.bold(self.apply_rule_on_other))
                )

        if self.price_or_product_discount == "Price" and not self.rate_or_discount:
            throw(
                _("Rate or Discount is required for the price discount."),
                frappe.MandatoryError,
            )

        if self.apply_discount_on_rate:
            if not self.priority:
                throw(
                    _(
                        "As the field {0} is enabled, the field {1} is mandatory."
                    ).format(
                        frappe.bold(_("Apply Discount on Discounted Rate")),
                        frappe.bold(_("Priority")),
                    )
                )

            if self.priority and cint(self.priority) == 1:
                throw(
                    _(
                        "As the field {0} is enabled, the value of the field {1} should be more than 1."
                    ).format(
                        frappe.bold(_("Apply Discount on Discounted Rate")),
                        frappe.bold(_("Priority")),
                    )
                )
