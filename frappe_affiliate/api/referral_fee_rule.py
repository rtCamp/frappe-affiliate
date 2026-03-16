import frappe

from frappe_affiliate.api.sales_invoice import get_invoice_count


@frappe.whitelist()
def get_referral_fee_rules(
    limit: int = 20,
    offset: int = 0,
    order_by: str = "priority asc",
    comment_filter: str | None = None,
):
    filters = {}
    if comment_filter:
        filters["comment"] = ["like", f"%{comment_filter}%"]
    referral_fee_rules_list = frappe.get_list(
        "Affiliate Referral Fee Rule",
        fields=[
            "name",
            "first_referral_rate",
            "subsequent_referral_rate",
            "disabled",
            "priority",
            "comment",
            "apply_on_group",
        ],
        order_by=order_by,
        limit_page_length=limit,
        limit_start=offset,
        filters=filters,
    )

    result = {}
    referral_fee_rules = []
    for referral_fee_rule in referral_fee_rules_list:
        rule_doc = frappe.get_doc("Affiliate Referral Fee Rule", referral_fee_rule.name)
        apply_on_items_code = [child.item_code for child in rule_doc.apply_on_item_code]
        apply_except_items_code = [
            child.item_code for child in rule_doc.apply_except_item_code
        ]
        apply_on_items = frappe.get_list(
            "Item", {"item_code": ["in", apply_on_items_code]}, pluck="item_name"
        )
        apply_except_items = frappe.get_list(
            "Item", {"item_code": ["in", apply_except_items_code]}, pluck="item_name"
        )
        apply_on_group = [
            referral_group.user_group for referral_group in rule_doc.apply_on_group
        ]
        apply_on_group_string = ", ".join(apply_on_group) if apply_on_group else ""
        referral_fee_rules.append(
            {
                "name": referral_fee_rule.name,
                "first_referral_rate": referral_fee_rule.first_referral_rate,
                "subsequent_referral_rate": referral_fee_rule.subsequent_referral_rate,
                "disabled": referral_fee_rule.disabled,
                "priority": referral_fee_rule.priority,
                "apply_on_item_code": apply_on_items,
                "apply_except_item_code": apply_except_items,
                "comment": referral_fee_rule.comment,
                "apply_on_group": apply_on_group_string,
            }
        )
    result["total"] = frappe.db.count("Affiliate Referral Fee Rule", filters=filters)
    result["rules"] = referral_fee_rules
    return result


def get_referral_fee_rule_for_tier(doc, group):
    invoice_item_codes = set(item.item_code for item in doc.items)
    referral_fee_rules = frappe.get_all(
        "Affiliate Referral Fee Rule",
        filters=[
            ["disabled", "=", 0],
            ["Referral User Group", "user_group", "in", group],
        ],
        fields=["name"],
    )

    referral_fee_rule = None

    invoice_count = get_invoice_count(doc)

    for rule in referral_fee_rules:
        rule_doc = frappe.get_doc("Affiliate Referral Fee Rule", rule.name)
        apply_on_rule_item_codes = set(
            child.item_code for child in rule_doc.apply_on_item_code
        )
        apply_except_rule_item_codes = set(
            child.item_code for child in rule_doc.apply_except_item_code
        )
        if (
            len(rule_doc.apply_on_item_code) == 0
            or invoice_item_codes.issubset(apply_on_rule_item_codes)
        ) and not invoice_item_codes.intersection(apply_except_rule_item_codes):
            if referral_fee_rule:
                if rule_doc.priority < referral_fee_rule.priority:
                    referral_fee_rule = rule_doc
            else:
                referral_fee_rule = rule_doc
            referral_fee_rule = rule_doc

    referral_fee_rate = None
    if referral_fee_rule:
        if invoice_count < 1:
            referral_fee_rate = referral_fee_rule.get("first_referral_rate", None)
        else:
            referral_fee_rate = referral_fee_rule.get("subsequent_referral_rate", None)

    return referral_fee_rate
