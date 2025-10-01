import frappe

from frappe_affiliate.api.sales_invoice import get_invoice_count


@frappe.whitelist()
def get_commission_rules():
    commission_rules_list = frappe.get_list(
        "Affiliate Commission Rule",
        fields=[
            "name",
            "first_commission",
            "subsequent_commission",
            "disabled",
            "priority",
            "comment",
            "apply_on_group",
        ],
        order_by="priority asc",
    )

    commission_rules = []
    for commission_rule in commission_rules_list:
        rule_doc = frappe.get_doc("Affiliate Commission Rule", commission_rule.name)
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
        commission_rules.append(
            {
                "name": commission_rule.name,
                "first_commission": commission_rule.first_commission,
                "subsequent_commission": commission_rule.subsequent_commission,
                "disabled": commission_rule.disabled,
                "priority": commission_rule.priority,
                "apply_on_item_code": apply_on_items,
                "apply_except_item_code": apply_except_items,
                "comment": commission_rule.comment,
                "apply_on_group": commission_rule.apply_on_group,
            }
        )
    return commission_rules


def get_commission_rule_for_tier(doc, group):
    invoice_item_codes = set(item.item_code for item in doc.items)
    commission_rules = frappe.get_all(
        "Affiliate Commission Rule",
        filters={"disabled": 0, "apply_on_group": group},
        fields=["name"],
    )

    commission_rule = None

    invoice_count = get_invoice_count(doc)

    for rule in commission_rules:
        rule_doc = frappe.get_doc("Affiliate Commission Rule", rule.name)
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
            if commission_rule:
                if rule_doc.priority < commission_rule.priority:
                    commission_rule = rule_doc
            else:
                commission_rule = rule_doc
            commission_rule = rule_doc

    commission_percent = None
    if commission_rule:
        if invoice_count < 1:
            commission_percent = commission_rule.get("first_commission", None)
        else:
            commission_percent = commission_rule.get("subsequent_commission", None)

    return commission_percent
