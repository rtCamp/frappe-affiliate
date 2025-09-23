import frappe


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
