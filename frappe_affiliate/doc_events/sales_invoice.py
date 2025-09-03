import frappe


def validate(doc, method=None):
    coupon_code = doc.get("coupon_code", None)
    if coupon_code:
        coupon_code_doc = frappe.get_doc("Coupon Code", coupon_code)
        if (
            coupon_code_doc.custom_sales_partner
            and coupon_code_doc.custom_sales_partner != doc.sales_partner
        ):
            doc.sales_partner = coupon_code_doc.custom_sales_partner

    if doc.sales_partner:
        from frappe_affiliate.api.sales_invoice import apply_commission_rules

        doc.commission_rate = apply_commission_rules(doc)
        doc.calculate_commission()
