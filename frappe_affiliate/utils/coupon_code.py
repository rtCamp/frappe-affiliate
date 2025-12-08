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
        user = frappe.session.user

        max_retries = 5  # Increased to 5 for timeout scenarios
        for attempt in range(max_retries):
            savepoint_name = f"{user}_coupon_update_{coupon_code_name}_{attempt}"

            try:
                # Create a savepoint before attempting the update
                frappe.db.savepoint(savepoint_name)

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

                # Success - release the savepoint and break out of retry loop
                frappe.db.release_savepoint(savepoint_name)
                break

            except Exception as e:
                error_type = (
                    "deadlock" if isinstance(e, frappe.QueryDeadlockError) else "other"
                )

                try:
                    frappe.db.rollback(save_point=savepoint_name)
                except Exception:
                    frappe.throw(
                        frappe._(
                            "Unable to apply changes to coupon code. Please try again."
                        )
                    )

                if attempt == max_retries - 1:
                    frappe.log_error(
                        title=f"Coupon Code Update Failed - {error_type}",
                        message=f"Failed after {max_retries} retries. Coupon: {coupon_code_name}, Type: {transaction_type}",
                    )
                    raise

                # Exponential backoff with jitter - more aggressive for timeouts
                base_delay = (
                    0.1 if error_type == "timeout" else 0.05
                )  # 100ms for timeout, 50ms for deadlock
                jitter = random.uniform(0.02, 0.6)  # 20ms to 600ms random jitter
                exponential_backoff = base_delay * (
                    2**attempt
                )  # Exponential: 50/100ms, 100/200ms, 200/400ms, 400/800ms, 800/1600ms
                total_delay = exponential_backoff + jitter

                frappe.logger().warning(
                    f"Coupon update {error_type} (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {total_delay * 1000:.0f}ms - Coupon: {coupon_code_name}"
                )

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
