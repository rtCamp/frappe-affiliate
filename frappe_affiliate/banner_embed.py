import frappe
from frappe import local
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response


def check_banner_embed():
    path = local.request.path
    banner_text_link_route_path = frappe.get_single_value(
        "Affiliate Settings", "banner_and_text_link_route_path"
    )
    if not path.startswith(banner_text_link_route_path):
        return

    path = path.strip(banner_text_link_route_path)
    parts = path.strip("/").split("/")
    parts_length = len(parts)

    if not parts_length == 2:
        return

    slug, username = parts

    banner_exists = frappe.db.exists(
        "Affiliate Banner and Text Link", {"name": slug, "disabled": 0}
    )
    if not banner_exists:
        return

    banner_text_link = frappe.get_doc("Affiliate Banner and Text Link", slug)

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
        js = f"""
        (function () {{
            var data = '<a href="{affiliate_link}" rel="nofollow" target="_blank">'
                + '<img src="{banner_url}" border="0" alt="{title}" width="100%" style="max-width:{banner_text_link.width or 728}px">'
                + '</a>';
            document.write(data);
        }})();
        """

    raise HTTPException(response=Response(js, content_type="application/javascript"))
