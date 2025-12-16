__version__ = "0.0.1"

import frappe
from erpnext.accounts.doctype.pricing_rule import utils as utils  # nosemgrep
from frappe import _
from frappe.utils import getdate, today


def monkey_patch():
    # ToDo: Debug and analyse the root cause why in some instances original function is called instead of monkey patched one.
    # For now the specific call is patched here to prevent this from happening.
    utils.validate_coupon_code = validate_coupon_code  # nosemgrep


def validate_coupon_code(coupon_name):
    if frappe.flags.in_migrate:
        return

    coupon = frappe.get_doc("Coupon Code", coupon_name)
    if coupon.valid_from and coupon.valid_from > getdate(today()):
        frappe.throw(_("Sorry, this coupon code's validity has not started"))
    elif coupon.valid_upto and coupon.valid_upto < getdate(today()):
        frappe.throw(_("Sorry, this coupon code's validity has expired"))
    elif coupon.maximum_use and coupon.used >= coupon.maximum_use:
        frappe.throw(_("Sorry, this coupon code is no longer valid"))
    elif (
        coupon.custom_subscription_maximum_use
        and coupon.custom_subscription_used_count
        >= coupon.custom_subscription_maximum_use
    ):
        frappe.throw(_("Sorry, this coupon code is no longer valid"))


try:
    monkey_patch()
except Exception as e:
    frappe.log_error(message=str(e), title="Frappe Affiliate Monkey Patch Failed")
    raise frappe.ValidationError("Frappe Affiliate Monkey Patch Failed: ", str(e))
