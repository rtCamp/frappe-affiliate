import random
import time

import frappe
from frappe import _ as translate
from frappe.utils import getdate, nowdate


def update_coupon_code_count(coupon_code_doc, transaction_type):
    if coupon_code_doc:
        coupon_code_name = (
            coupon_code_doc.name
            if hasattr(coupon_code_doc, "name")
            else coupon_code_doc
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if transaction_type == "used":
                    frappe.db.sql(
                        """
                        UPDATE `tabCoupon Code`
                        SET custom_subscription_used_count = custom_subscription_used_count + 1,
                            modified = %s
                        WHERE name = %s
                        AND (custom_subscription_maximum_use IS NULL
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

                # Success - break out of retry loop
                break

            except frappe.QueryDeadlockError:
                if attempt == max_retries - 1:
                    # Last attempt failed, re-raise the error
                    raise

                # Random backoff to avoid concurrent retries colliding
                base_delay = 0.05  # 50ms base
                jitter = random.uniform(0.01, 0.5)  # 10ms to 500ms random jitter
                exponential_backoff = base_delay * (
                    2**attempt
                )  # Exponential: 50ms, 100ms, 200ms
                total_delay = exponential_backoff + jitter + random.random() * 0.1

                time.sleep(total_delay)
                continue


def validate_coupon_code(
    coupon_code_doc, customer=None, is_new_subscription=False
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
