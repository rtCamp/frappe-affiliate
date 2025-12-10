__version__ = "0.0.1"

import frappe
from erpnext.accounts.doctype.pricing_rule import utils as utils  # nosemgrep
from erpnext.accounts.doctype.pricing_rule.utils import (
    _get_tree_conditions,
    get_other_conditions,
)
from frappe import _
from frappe.utils import getdate, today


def monkey_patch():
    # ToDo: Debug and analyse the root cause why in some instances original function is called instead of monkey patched one.
    # For now the specific call is patched here to prevent this from happening.
    utils.validate_coupon_code = validate_coupon_code  # nosemgrep
    utils._get_pricing_rules = _get_pricing_rules  # nosemgrep


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


def _get_pricing_rules(apply_on, args, values):
    apply_on_field = frappe.scrub(apply_on)

    if not args.get(apply_on_field):
        return []

    child_doc = f"`tabPricing Rule {apply_on}`"

    conditions = item_variant_condition = item_conditions = ""
    values[apply_on_field] = args.get(apply_on_field)
    if apply_on_field in ["item_code", "brand"]:
        item_conditions = f"{child_doc}.{apply_on_field}= %({apply_on_field})s"

        if apply_on_field == "item_code":
            if args.get("uom", None):
                item_conditions += " and ({child_doc}.uom={item_uom} or IFNULL({child_doc}.uom, '')='')".format(
                    child_doc=child_doc, item_uom=frappe.db.escape(args.get("uom"))
                )
            if "variant_of" not in args:
                args.variant_of = frappe.get_cached_value(
                    "Item", args.item_code, "variant_of"
                )

            if args.variant_of:
                item_variant_condition = f" or {child_doc}.item_code=%(variant_of)s "
                values["variant_of"] = args.variant_of
    elif apply_on_field == "item_group":
        item_conditions = _get_tree_conditions(args, "Item Group", child_doc, False)
        if args.get("uom", None):
            item_conditions += " and ({child_doc}.uom={item_uom} or IFNULL({child_doc}.uom, '')='')".format(
                child_doc=child_doc, item_uom=frappe.db.escape(args.get("uom"))
            )

    conditions += get_other_conditions(conditions, values, args)
    warehouse_conditions = _get_tree_conditions(args, "Warehouse", "`tabPricing Rule`")
    if warehouse_conditions:
        warehouse_conditions = f" and {warehouse_conditions}"

    if not args.price_list:
        args.price_list = None

    conditions += (
        " and ifnull(`tabPricing Rule`.for_price_list, '') in (%(price_list)s, '')"
    )
    values["price_list"] = args.get("price_list")

    pricing_rules = (
        frappe.db.sql(
            """select `tabPricing Rule`.*,
			{child_doc}.{apply_on_field}, {child_doc}.uom
		from `tabPricing Rule`, {child_doc}
		where ({item_conditions} or (`tabPricing Rule`.apply_rule_on_other is not null
			and `tabPricing Rule`.{apply_on_other_field}=%({apply_on_field})s) {item_variant_condition})
			and {child_doc}.parent = `tabPricing Rule`.name
			and `tabPricing Rule`.disable = 0 and
			`tabPricing Rule`.{transaction_type} = 1 {warehouse_cond} {conditions}
			and `tabPricing Rule`.coupon_code_based = 0
		order by `tabPricing Rule`.priority desc,
			`tabPricing Rule`.name desc""".format(
                child_doc=child_doc,
                apply_on_field=apply_on_field,
                item_conditions=item_conditions,
                item_variant_condition=item_variant_condition,
                transaction_type=args.transaction_type,
                warehouse_cond=warehouse_conditions,
                apply_on_other_field=f"other_{apply_on_field}",
                conditions=conditions,
            ),
            values,
            as_dict=1,
        )
        or []
    )

    return pricing_rules


def get_invoice_count(doc):
    count = frappe.db.count(
        "Sales Invoice",
        {"customer": doc.customer, "subscription": doc.subscription, "docstatus": 1},
    )
    return count


try:
    monkey_patch()
except Exception as e:
    frappe.log_error(message=str(e), title="Frappe Affiliate Monkey Patch Failed")
    raise frappe.ValidationError("Frappe Affiliate Monkey Patch Failed: ", str(e))
