__version__ = "0.0.1"

import json

import frappe
from erpnext.accounts.doctype.pricing_rule import pricing_rule
from erpnext.accounts.doctype.pricing_rule.pricing_rule import (
    apply_price_discount_rule,
    get_pricing_rule_details,
    remove_pricing_rule_for_item,
    update_args_for_pricing_rule,
    update_pricing_rule_uom,
)


def monkey_patch():
    # nosemgrep
    pricing_rule.get_pricing_rule_for_item = get_pricing_rule_for_item


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

                coupon_fieldname = "pricing_rule"
                if doc.doctype == "Sales Invoice" and not args.get("is_return"):
                    recurring_coupon = frappe.db.get_value(
                        doctype="Coupon Code",
                        filters={"name": args.coupon_code},
                        fieldname="custom_is_recurring",
                    )
                    from frappe_affiliate.api.sales_invoice import get_invoice_count

                    invoice_count = get_invoice_count(doc)
                    if invoice_count >= 1 and recurring_coupon:
                        coupon_fieldname = "custom_second_pricing_rule"
                    elif invoice_count >= 1 and not recurring_coupon:
                        continue

                coupon_pricing_rule = frappe.db.get_value(
                    doctype="Coupon Code",
                    filters={"name": args.coupon_code},
                    fieldname=coupon_fieldname,
                )

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


try:
    # nosemgrep
    monkey_patch()
except Exception:
    pass
