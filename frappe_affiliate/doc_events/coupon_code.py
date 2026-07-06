import frappe
from frappe import _


def on_update(doc, method):
    if not doc.custom_sales_partner:
        return

    if doc.has_value_changed("custom_sales_partner") and (
        doc.custom_subscription_used_count > 1 or doc.used > 1
    ):
        frappe.throw(_("Linked affiliate cannot be changed once coupon is used."))
