import frappe
from frappe import _ as translate
from frappe.utils import getdate, nowdate


def update_coupon_code_count(coupon_code_doc, transaction_type):
    coupon_code_name = coupon_code_doc.name
    if transaction_type == "used":
        frappe.db.sql(
            """
                UPDATE `tabCoupon Code`
                SET custom_subscription_used_count = custom_subscription_used_count + 1,
                    modified = %s
                    WHERE name = %s
                    AND (custom_subscription_maximum_use = 0
                OR custom_subscription_maximum_use IS NULL
                OR custom_subscription_used_count < custom_subscription_maximum_use)
                    """,
            (frappe.utils.now(), coupon_code_name),
        )

        rows_affected = frappe.db.sql("""SELECT ROW_COUNT();""")[0][0]
        if not rows_affected:
            frappe.throw(translate("Allowed quantity is exhausted"))

    elif transaction_type == "cancelled":
        frappe.db.sql(
            """
                UPDATE `tabCoupon Code`
                SET custom_subscription_used_count = GREATEST(custom_subscription_used_count - 1, 0),
                    modified = %s
                WHERE name = %s
                AND custom_subscription_used_count > 0
            """,
            (frappe.utils.now(), coupon_code_name),
        )


def validate_coupon_code(
    coupon_code_doc, customer=None, is_new_subscription=False, item=None
) -> bool:
    if not coupon_code_doc:
        return False

    if isinstance(coupon_code_doc, str):
        coupon_doc_name = frappe.db.exists(
            "Coupon Code", {"coupon_code": coupon_code_doc}
        )
        if not coupon_doc_name:
            return False
        coupon_code_doc = frappe.get_doc("Coupon Code", coupon_doc_name)

    if is_new_subscription and coupon_code_doc.custom_disable:
        return False
    elif coupon_code_doc.valid_from and getdate(coupon_code_doc.valid_from) > getdate(
        nowdate()
    ):
        return False
    elif coupon_code_doc.valid_upto and getdate(coupon_code_doc.valid_upto) < getdate(
        nowdate()
    ):
        return False
    elif (
        coupon_code_doc.maximum_use
        and coupon_code_doc.used >= coupon_code_doc.maximum_use
    ):
        return False
    elif (
        coupon_code_doc.custom_subscription_maximum_use
        and coupon_code_doc.custom_subscription_used_count
        >= coupon_code_doc.custom_subscription_maximum_use
    ):
        return False

    if coupon_code_doc.customer and coupon_code_doc.customer != customer:
        return False

    if customer and is_new_subscription:
        if not check_user_use_count(coupon_code_doc, customer):
            return False

    if item:
        coupon_batch = coupon_code_doc.get("custom_coupon_batch", None)
        if coupon_batch:
            if not check_item_in_coupon_batch([item], coupon_batch):
                return False

    if coupon_code_doc.custom_sales_partner:
        affiliate_banned = frappe.db.get_value(
            "Sales Partner",
            coupon_code_doc.custom_sales_partner,
            ["custom_banned", "custom_disabled"],
            as_dict=True,
        )
        if affiliate_banned.custom_disabled or affiliate_banned.custom_banned:
            return False

    return True


def check_user_use_count(coupon_code_doc, customer):
    coupon_user_use_count = coupon_code_doc.get("custom_maximum_user_use_count", 0)
    if coupon_user_use_count > 0:
        user_use_count = frappe.db.count(
            "Subscription",
            {
                "party_type": "Customer",
                "party": customer,
                "custom_coupon_code": coupon_code_doc.name,
                "status": ["not in", ["Pending", "Unpaid"]],
            },
        )
        if user_use_count >= coupon_user_use_count:
            return False

    return True


def check_item_in_coupon_batch(item_list, coupon_batch):
    apply_on_specific = frappe.get_all(
        "Pricing Rule Item Code",
        filters={
            "parent": coupon_batch,
            "parenttype": "Coupon Batch",
            "parentfield": "apply_on_item_code",
        },
        fields=["item_code"],
        pluck="item_code",
    )
    if apply_on_specific and apply_on_specific != []:
        applies = set(item_list).issubset(apply_on_specific)
        if not applies:
            return False
    apply_except = frappe.get_all(
        "Pricing Rule Item Code",
        filters={
            "parent": coupon_batch,
            "parenttype": "Coupon Batch",
            "item_code": ["in", item_list],
            "parentfield": "apply_except_item_code",
        },
    )
    if apply_except and apply_except != []:
        return False
    return True


def calculate_higher_discount(discount, promo_offer, price):
    if not promo_offer:
        return discount

    promo_discount_value = None
    normal_discount_value = None

    if promo_offer["type"] == "Percentage":
        promo_discount_value = (promo_offer["value"] / 100) * price
    elif promo_offer["type"] == "Amount":
        promo_discount_value = promo_offer["value"]

    if discount["type"] == "Percentage":
        normal_discount_value = (discount["value"] / 100) * price
    elif discount["type"] == "Amount":
        normal_discount_value = discount["value"]

    if promo_discount_value > normal_discount_value:
        return promo_offer
    return discount


def get_first_recurring_discount(coupon_code, recurring=False, plans=None):
    result = {
        "type": None,
        "value": 0.0,
    }

    promotional_offer = _apply_promotional_offer_hooks(
        coupon_code, plans=plans, recurring=recurring
    )

    if not coupon_code:
        return result, None

    coupon_batch = frappe.get_value("Coupon Code", coupon_code, "custom_coupon_batch")

    if not coupon_batch:
        return result, None

    coupon_batch_values = frappe.db.get_value(
        "Coupon Batch",
        coupon_batch,
        [
            "rate_or_discount",
            "discount",
            "recurring_rate_or_discount",
            "recurring_discount",
            "apply_to_recurring",
        ],
        as_dict=True,
    )

    if not coupon_batch_values:
        return result, None
    if recurring and not coupon_batch_values.get("apply_to_recurring"):
        return result, None

    recurring_string = "recurring_" if recurring else ""

    result["type"] = coupon_batch_values.get(f"{recurring_string}rate_or_discount")
    result["value"] = coupon_batch_values.get(f"{recurring_string}discount") or 0.0
    return result, promotional_offer


def _apply_promotional_offer_hooks(coupon_code, plans=None, recurring=False):
    """
    Allow other apps to hook into and modify the coupon discount logic via the
    'apply_promotional_offer' hook.

    Each hook method should return discount details as a dict with keys:
      - type: either "Percentage" or "Amount"
      - value: the discount value as a float
      - recurring: bool indicating if the discount is for recurring charges
    By default the last hook will be applied.

    Example (in another app's hooks.py):
        apply_promotional_offer = [
            "my_app.promo_hooks.apply_summer_sale_discount",
        ]

    Example hook implementation:
        def apply_summer_sale_discount(coupon_code, plans=None):
            return {
                "type": "Percentage",
                "value": 20.0
            }

    Params:
        coupon_code (str): The coupon code to evaluate.
        plans (list, optional): List of plans to check for promotions. Defaults to None.
    """
    method_path = None
    hooks = frappe.get_hooks("apply_promotional_offer") or []
    if hooks and len(hooks) > 0:
        method_path = hooks[-1]
    if method_path:
        try:
            method = frappe.get_attr(method_path)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(), "apply_promotional_offer hook import failure"
            )
            return None
        try:
            result = method(coupon_code=coupon_code, plans=plans, recurring=recurring)
            if result is None:
                return None
            else:
                return result
        except Exception:
            frappe.log_error(
                frappe.get_traceback(), "apply_promotional_offer hook execution failure"
            )
