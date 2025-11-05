__version__ = "0.0.1"

import json

import frappe
from apps.erpnext.erpnext.accounts.doctype.pricing_rule.utils import (
    get_other_conditions,
)
from erpnext.accounts.doctype.pricing_rule import (  # nosemgrep
    pricing_rule as pricing_rule,  # nosemgrep
)
from erpnext.accounts.doctype.pricing_rule import utils as utils  # nosemgrep
from erpnext.accounts.doctype.pricing_rule.pricing_rule import (
    apply_price_discount_rule,
    get_pricing_rule_details,
    remove_pricing_rule_for_item,
    update_args_for_pricing_rule,
    update_pricing_rule_uom,
)
from erpnext.accounts.doctype.pricing_rule.utils import _get_tree_conditions
from frappe import _
from frappe.utils import getdate, today

from frappe_affiliate.api.sales_invoice import get_invoice_count


def monkey_patch():
    pricing_rule.get_pricing_rule_for_item = get_pricing_rule_for_item  # nosemgrep
    utils.validate_coupon_code = validate_coupon_code  # nosemgrep
    utils._get_pricing_rules = _get_pricing_rules  # nosemgrep


def get_pricing_rule_for_item(args, doc=None, for_validate=False):
    from erpnext.accounts.doctype.pricing_rule.utils import (
        get_applied_pricing_rules,
        get_pricing_rule_items,
        get_pricing_rules,
        get_product_discount_rule,
    )

    if isinstance(doc, str):
        doc = json.loads(doc)

    if doc:
        doc = frappe.get_doc(doc)

    if args.get("is_free_item") or args.get("parenttype") == "Material Request":
        return {}

    item_details = frappe._dict(
        {
            "doctype": args.doctype,
            "has_margin": False,
            "name": args.name,
            "free_item_data": [],
            "parent": args.parent,
            "parenttype": args.parenttype,
            "child_docname": args.get("child_docname"),
        }
    )

    if args.ignore_pricing_rule or not args.item_code:
        if frappe.db.exists(args.doctype, args.name) and args.get("pricing_rules"):
            item_details = remove_pricing_rule_for_item(
                args.get("pricing_rules"),
                item_details,
                item_code=args.get("item_code"),
                rate=args.get("price_list_rate"),
            )
        return item_details

    update_args_for_pricing_rule(args)

    pricing_rules = (
        get_applied_pricing_rules(args.get("pricing_rules"))
        if for_validate and args.get("pricing_rules")
        else get_pricing_rules(args, doc)
    )

    coupon_pricing_rule = None
    if args.get("coupon_code", None):
        coupon_fieldname = "pricing_rule"
        if doc.doctype == "Sales Invoice" and not args.get("is_return"):
            coupon_values = frappe.db.get_value(
                doctype="Coupon Code",
                filters={"name": args.get("coupon_code")},
                fieldname=[
                    "custom_apply_to_recurring",
                    "pricing_rule",
                    "custom_recurring_pricing_rule",
                ],
                as_dict=True,
            )

            invoice_count = get_invoice_count(doc)
            if invoice_count >= 1 and coupon_values.get("custom_apply_to_recurring"):
                coupon_fieldname = "custom_recurring_pricing_rule"
            elif invoice_count >= 1 and not coupon_values.get(
                "custom_apply_to_recurring"
            ):
                coupon_fieldname = None
        if coupon_fieldname:
            coupon_pricing_rule = coupon_values.get(coupon_fieldname)
            if not (for_validate and args.get("pricing_rules")):
                pricing_rules.append(coupon_pricing_rule)

    if pricing_rules:
        rules = []

        for pricing_rule in pricing_rules:
            if not pricing_rule:
                continue

            if isinstance(pricing_rule, str):
                pricing_rule = frappe.get_cached_doc("Pricing Rule", pricing_rule)
                update_pricing_rule_uom(pricing_rule, args)
                fetch_other_item = True if pricing_rule.apply_rule_on_other else False
                pricing_rule.apply_rule_on_other_items = (
                    get_pricing_rule_items(pricing_rule, other_items=fetch_other_item)
                    or []
                )

            if pricing_rule.coupon_code_based == 1:
                if not args.coupon_code:
                    continue

                if pricing_rule.name != coupon_pricing_rule:
                    continue

            if pricing_rule.get("suggestion"):
                continue

            item_details.validate_applied_rule = pricing_rule.get(
                "validate_applied_rule", 0
            )
            item_details.price_or_product_discount = pricing_rule.get(
                "price_or_product_discount"
            )

            rules.append(get_pricing_rule_details(args, pricing_rule))

            if pricing_rule.mixed_conditions or pricing_rule.apply_rule_on_other:
                item_details.update(
                    {
                        "price_or_product_discount": pricing_rule.price_or_product_discount,
                        "apply_rule_on": (
                            frappe.scrub(pricing_rule.apply_rule_on_other)
                            if pricing_rule.apply_rule_on_other
                            else frappe.scrub(pricing_rule.get("apply_on"))
                        ),
                    }
                )

                if pricing_rule.apply_rule_on_other_items:
                    item_details["apply_rule_on_other_items"] = json.dumps(
                        pricing_rule.apply_rule_on_other_items
                    )

            if not pricing_rule.validate_applied_rule:
                if pricing_rule.price_or_product_discount == "Price":
                    apply_price_discount_rule(pricing_rule, item_details, args)
                else:
                    get_product_discount_rule(pricing_rule, item_details, args, doc)

        if not item_details.get("has_margin"):
            item_details.margin_type = None
            item_details.margin_rate_or_amount = 0.0

        item_details.has_pricing_rule = 1

        item_details.pricing_rules = frappe.as_json([d.pricing_rule for d in rules])

        if not doc:
            return item_details

    elif args.get("pricing_rules"):
        item_details = remove_pricing_rule_for_item(
            args.get("pricing_rules"),
            item_details,
            item_code=args.get("item_code"),
            rate=args.get("price_list_rate"),
        )

    return item_details


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


try:
    monkey_patch()
except Exception as e:
    frappe.log_error(message=str(e), title="Frappe Affiliate Monkey Patch Failed")
    raise frappe.ValidationError("Frappe Affiliate Monkey Patch Failed: ", str(e))
