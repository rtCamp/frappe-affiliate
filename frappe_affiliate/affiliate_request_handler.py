import frappe
from frappe import local
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response


def handle_affiliate_routes():
    path = local.request.path
    affiliate_settings = frappe.get_cached_doc("Affiliate Settings")
    cookie_route_path = affiliate_settings.affiliate_route_path
    banner_text_link_route_path = affiliate_settings.banner_and_text_link_route_path

    if path.startswith(banner_text_link_route_path):
        check_banner_embed(banner_text_link_route_path)
    elif path.startswith(cookie_route_path):
        set_cookie(cookie_route_path, affiliate_settings.cookie_timeout)
    else:
        return


def set_cookie(cookie_route_path, cookie_timeout=30):
    path = local.request.path
    parts = path[len(cookie_route_path) :].strip("/").split("/")
    parts_length = len(parts)

    if not parts_length == 1:
        return

    username = parts[0]

    response = Response("", content_type="text/html")
    response.set_cookie("affiliate_id", username, max_age=60 * 60 * 24 * cookie_timeout)
    response.headers["Location"] = "/member"
    response.status_code = 302
    raise HTTPException(response=response)


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
        "Sales Partner", {"custom_user": user, "custom_banned": 0}
    )
    if not affiliate_exists:
        return
    affiliate_link = frappe.db.get_value(
        "Sales Partner",
        {"custom_user": user, "custom_banned": 0},
        "custom_affiliate_link",
    )

    if item_type == "Text Link":
        js = f"""
        (function () {{
            var data = '<a href="{affiliate_link}" rel="nofollow" target="_top">{title}</a>';
            document.write(data);
        }})();
        """
    else:
        target_attr = (
            "_blank" if banner_text_link.get("open_in_new_window", False) else "_top"
        )
        js = f"""
        (function () {{
            var data = '<a href="{affiliate_link}" rel="nofollow" target="{target_attr}">'
            + '<img src="{banner_url}" border="0" alt="{title}" width="100%" style="max-width:{banner_text_link.width or 728}px">'
            + '</a>';
            document.write(data);
        }})();
        """

    raise HTTPException(response=Response(js, content_type="application/javascript"))
