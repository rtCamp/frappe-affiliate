import frappe
from frappe import _


def on_update(doc, method):
    if doc.has_value_changed("custom_sales_partner") and (
        (doc.custom_subscription_used_count or 0) > 0 or (doc.used or 0) > 0
    ):
        frappe.throw(_("Linked affiliate cannot be changed once coupon is used."))
