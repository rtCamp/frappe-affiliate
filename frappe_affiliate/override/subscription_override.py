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

        # Function had to be overridden to add custom coupon code here just before pricing rule related functions are executed.
        if self.get("custom_coupon_code", None):
            invoice.coupon_code = self.custom_coupon_code

        invoice.set_missing_values()

        invoice.save()

        if self.submit_invoice:
            invoice.submit()

        return invoice

    def is_trialling(self) -> bool:
        """
        Returns `True` if the `Subscription` is in trial period.
        """
        return not self.period_has_passed(self.trial_period_end)
