import frappe
from frappe import local
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response

from frappe_affiliate.api.affiliate_click_log import record_click


def handle_affiliate_routes():
    path = local.request.path
    affiliate_settings = frappe.get_cached_doc("Affiliate Settings")
    cookie_route_path = affiliate_settings.affiliate_route_path
    banner_text_link_route_path = affiliate_settings.banner_and_text_link_route_path

    if not (cookie_route_path or banner_text_link_route_path):
        return

    if path.startswith(banner_text_link_route_path):
        check_banner_embed(banner_text_link_route_path)
    elif path.startswith(cookie_route_path):
        set_cookie(cookie_route_path, affiliate_settings.cookie_timeout)
    else:
        return


def set_cookie(cookie_route_path, cookie_timeout):
    if not cookie_timeout:
        cookie_timeout = 30

    path = local.request.path
    parts = path[len(cookie_route_path) :].strip("/").split("/")
    parts_length = len(parts)

    if not parts_length == 1:
        return

    username = parts[0]

    if not username:
        return

    affiliate_redirect_url = frappe.get_cached_doc(
        "Affiliate Settings"
    ).affiliate_redirect_url
    banner_url = affiliate_redirect_url if affiliate_redirect_url else "/"

    response = Response("", content_type="text/html")

    user_exists = frappe.db.exists("User", {"username": username, "enabled": 1})
    if not user_exists:
        redirect_affiliate_link(banner_url, response)

    affiliate_exists = frappe.db.exists(
        "Sales Partner",
        {"custom_user": user_exists, "custom_banned": 0, "custom_disabled": 0},
    )

    if not affiliate_exists:
        redirect_affiliate_link(banner_url, response)

    banner = frappe.local.request.args.get("banner")
    banner_exists = frappe.db.exists(
        "Affiliate Banner and Text Link", {"name": banner, "disabled": 0}
    )
    if banner_exists:
        banner_url = get_banner_redirect_url(banner)
    cookie_val = local.request.cookies.get("affiliate_id")
    new_val = None

    if cookie_val:
        cookie_val_length = len(cookie_val.split("-"))
        cookie_split = cookie_val.split("-") if cookie_val else []
        if cookie_val_length == 2 and banner_exists:
            click = record_click(username, banner)
            new_val = f"{username}-{banner}-{click}"
        elif cookie_val_length == 2 and not banner_exists:
            if cookie_split[0] != username:
                click = record_click(username, None)
                new_val = f"{username}-{click}"
        elif cookie_val_length == 3 and banner_exists:
            if (
                not cookie_val
                or "-".join(cookie_val.split("-", 2)[:2]) != f"{username}-{banner}"
            ):
                click = record_click(username, banner)
                new_val = f"{username}-{banner}-{click}"
        elif cookie_val_length == 3 and not banner_exists:
            if cookie_split[0] != username:
                click = record_click(username, None)
                new_val = f"{username}-{click}"
    else:
        if not banner_exists:
            click = record_click(username, None)
            new_val = f"{username}-{click}"
        else:
            click = record_click(username, banner)
            new_val = f"{username}-{banner}-{click}"

    if new_val:
        response.set_cookie(
            "affiliate_id", new_val, max_age=60 * 60 * 24 * cookie_timeout
        )

    redirect_affiliate_link(banner_url, response)


def get_banner_redirect_url(banner):
    if not banner:
        return None

    banner_text_link = frappe.get_value(
        "Affiliate Banner and Text Link", banner, "redirect_url"
    )
    return banner_text_link or "/"


def check_banner_embed(banner_text_link_route_path):
    path = local.request.path
    parts = path[len(banner_text_link_route_path) :].strip("/").split("/")
    parts_length = len(parts)

    if not parts_length == 2:
        return

    slug, username = parts

    banner_exists = frappe.db.exists(
        "Affiliate Banner and Text Link", {"name": slug, "disabled": 0}
    )
    if not banner_exists:
        return

    banner_text_link = frappe.get_cached_doc("Affiliate Banner and Text Link", slug)

    item_type = banner_text_link.type or "Text Link"
    title = banner_text_link.title or ""
    banner = banner_text_link.banner
    banner_url = (
        frappe.utils.get_url(frappe.db.get_value("File", banner, "file_url"))
        if banner
        else ""
    )

    affiliate_user = frappe.db.exists("User", {"username": username, "enabled": 1})
    if not affiliate_user:
        return
    user = frappe.db.get_value("User", {"username": username, "enabled": 1}, "name")
    affiliate_exists = frappe.db.exists(
        "Sales Partner", {"custom_user": user, "custom_banned": 0, "custom_disabled": 0}
    )
    if not affiliate_exists:
        return
    affiliate_link = frappe.db.get_value(
        "Sales Partner",
        {"custom_user": user, "custom_banned": 0, "custom_disabled": 0},
        "custom_affiliate_link",
    )

    if item_type == "Text Link":
        js = f"""
        (function () {{
            var data = '<a href="{affiliate_link}?banner={banner_text_link.name}" rel="nofollow" target="_top">{title}</a>';
            document.write(data);
        }})();
        """
    else:
        target_attr = (
            "_blank" if banner_text_link.get("open_in_new_window", False) else "_top"
        )
        js = f"""
        (function () {{
            var data = '<a href="{affiliate_link}?banner={banner_text_link.name}" rel="nofollow" target="{target_attr}">'
            + '<img src="{banner_url}" border="0" alt="{title}" width="100%" style="max-width:{banner_text_link.width or 728}px">'
            + '</a>';
            document.write(data);
        }})();
        """

    raise HTTPException(response=Response(js, content_type="application/javascript"))


def redirect_affiliate_link(redirect_url, response):
    response.headers["Location"] = redirect_url
    response.status_code = 302
    raise HTTPException(response=response)
