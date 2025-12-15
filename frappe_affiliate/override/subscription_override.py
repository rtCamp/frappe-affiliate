from datetime import date

import frappe
from erpnext import get_default_company
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
)
from erpnext.accounts.doctype.subscription.subscription import Subscription, is_prorate
from frappe import _
from frappe.utils.data import (
    add_days,
    cint,
)

from frappe_affiliate.utils.coupon_code import (
    get_first_recurring_discount,
)

DateTimeLikeObject = str | date


class SubscriptionOverride(Subscription):
    def create_invoice(
        self,
        from_date: DateTimeLikeObject | None = None,
        to_date: DateTimeLikeObject | None = None,
        posting_date: DateTimeLikeObject | None = None,
    ):
        """
        Creates a `Invoice`, submits it and returns it
        """
        # For backward compatibility
        # Earlier subscription didn't had any company field
        company = self.get("company") or get_default_company()
        if not company:
            frappe.throw(
                _(
                    "Company is mandatory for generating an invoice. Please set a default company in Global Defaults."
                )
            )

        invoice = frappe.new_doc(self.invoice_document_type)
        invoice.company = company
        invoice.set_posting_time = 1

        if self.generate_invoice_at == "Beginning of the current subscription period":
            invoice.posting_date = self.current_invoice_start
        elif self.generate_invoice_at == "Days before the current subscription period":
            invoice.posting_date = posting_date or self.current_invoice_start
        else:
            invoice.posting_date = self.current_invoice_end

        invoice.cost_center = self.cost_center

        if self.invoice_document_type == "Sales Invoice":
            invoice.customer = self.party
        else:
            invoice.supplier = self.party
            if frappe.db.get_value("Supplier", self.party, "tax_withholding_category"):
                invoice.apply_tds = 1

        # Add currency to invoice
        invoice.currency = frappe.db.get_value(
            "Subscription Plan", {"name": self.plans[0].plan}, "currency"
        )

        # Add dimensions in invoice for subscription:
        accounting_dimensions = get_accounting_dimensions()

        for dimension in accounting_dimensions:
            if self.get(dimension):
                invoice.update({dimension: self.get(dimension)})

        # Subscription is better suited for service items. I won't update `update_stock`
        # for that reason
        items_list = self.get_items_from_plans(self.plans, is_prorate())

        for item in items_list:
            item["cost_center"] = self.cost_center
            invoice.append("items", item)

        # Taxes
        tax_template = ""

        if self.invoice_document_type == "Sales Invoice" and self.sales_tax_template:
            tax_template = self.sales_tax_template
        if (
            self.invoice_document_type == "Purchase Invoice"
            and self.purchase_tax_template
        ):
            tax_template = self.purchase_tax_template

        if tax_template:
            invoice.taxes_and_charges = tax_template
            invoice.set_taxes()

        # Due date
        if self.days_until_due:
            invoice.append(
                "payment_schedule",
                {
                    "due_date": add_days(
                        invoice.posting_date, cint(self.days_until_due)
                    ),
                    "invoice_portion": 100,
                },
            )

        # Discounts
        if self.is_trialling():
            invoice.additional_discount_percentage = 100
        else:
            if self.additional_discount_percentage:
                invoice.additional_discount_percentage = (
                    self.additional_discount_percentage
                )

            if self.additional_discount_amount:
                invoice.discount_amount = self.additional_discount_amount

            if self.additional_discount_percentage or self.additional_discount_amount:
                discount_on = self.apply_additional_discount
                invoice.apply_discount_on = (
                    discount_on if discount_on else "Grand Total"
                )

        # Subscription period
        invoice.subscription = self.name
        invoice.from_date = from_date or self.current_invoice_start
        invoice.to_date = to_date or self.current_invoice_end

        invoice.flags.ignore_mandatory = True

        subscription_current_first_cost = self.get("custom_first_cost", None)
        first_recurring_cost_set = (
            True
            if subscription_current_first_cost and subscription_current_first_cost > 0
            else False
        )

        # Function had to be overridden to add custom coupon code here just before pricing rule related functions are executed.
        if self.get("custom_coupon_code", None):
            invoice.coupon_code = self.custom_coupon_code
            if not first_recurring_cost_set:
                first_discount = get_first_recurring_discount(
                    invoice.coupon_code, recurring=False, plans=self.plans
                )
                if first_discount["type"] == "Percentage":
                    invoice.additional_discount_percentage = (
                        (
                            invoice.additional_discount_percentage
                            + first_discount["value"]
                        )
                        if invoice.additional_discount_percentage
                        else first_discount["value"]
                    )
                elif first_discount["type"] == "Amount":
                    invoice.discount_amount = (
                        (invoice.discount_amount + first_discount["value"])
                        if invoice.discount_amount
                        else first_discount["value"]
                    )
                invoice.apply_discount_on = "Net Total"

        invoice.set_missing_values()

        invoice.save()

        invoice.reload()

        net_total = invoice.total

        if self.get("custom_coupon_code", None) and not first_recurring_cost_set:
            first_cost = invoice.net_total
            recurring_cost = calculate_recurring_cost(
                invoice.coupon_code, self.plans, net_total
            )
            frappe.db.set_value(
                "Subscription",
                self.name,
                {
                    "custom_first_cost": first_cost,
                    "custom_recurring_cost": recurring_cost,
                },
            )
            self.reload()
        elif not first_recurring_cost_set:
            frappe.db.set_value(
                "Subscription",
                self.name,
                {
                    "custom_first_cost": net_total,
                    "custom_recurring_cost": net_total,
                },
            )
            self.reload()

        if self.submit_invoice:
            invoice.submit()

        return invoice

    def is_trialling(self) -> bool:
        """
        Returns `True` if the `Subscription` is in trial period.
        """
        return not self.period_has_passed(self.trial_period_end)


def calculate_recurring_cost(coupon_code, plans, net_total):
    recurring_discount = get_first_recurring_discount(
        coupon_code, recurring=True, plans=plans
    )
    recurring_override = _apply_recurring_discount_hooks(
        coupon_code=coupon_code,
        recurring_discount=recurring_discount,
        plans=plans,
        net_total=net_total,
    )
    if recurring_override is not None:
        return recurring_override

    if recurring_discount["type"] == "Percentage":
        discount_value = (recurring_discount["value"] / 100) * net_total
    elif recurring_discount["type"] == "Amount":
        discount_value = recurring_discount["value"]
    else:
        discount_value = 0.0
    recurring_cost = net_total - discount_value
    return max(0, min(recurring_cost, net_total))


def _apply_recurring_discount_hooks(
    coupon_code, recurring_discount, plans, net_total=0.0
):
    """
    Allow other apps to hook into and modify the recurring discount logic via the
    'recurring_discount_override' hook.

    Each hook method should return discounted amount as a float.:

    Example (in another app's hooks.py):
        recurring_discount_override = [
            "my_app.promo_hooks.apply_summer_sale_discount",
        ]

    Example hook implementation:
        def apply_summer_sale_discount(coupon_code, plans, net_total=0.0):
            return 20.0

    Params:
        coupon_code (str): The coupon code to evaluate.
        recurring_discount (dict): The recurring discount details.
        plans (list): List of plans to check for promotions.
        net_total (float, optional): net amount before taxation on first invoice. Defaults to 0.0.
    """
    hooks = frappe.get_hooks("recurring_discount_override") or []
    method_path = None
    if hooks and len(hooks) > 0:
        method_path = hooks[-1]
    if method_path:
        try:
            method = frappe.get_attr(method_path)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "recurring_discount_override hook import failure",
            )
            return None
        try:
            result = method(
                coupon_code=coupon_code,
                recurring_discount=recurring_discount,
                plans=plans,
                net_total=net_total,
            )
            if result is None:
                return None
            else:
                return result
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "recurring_discount_override hook execution failure",
            )
