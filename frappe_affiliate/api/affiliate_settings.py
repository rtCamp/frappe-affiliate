import frappe


@frappe.whitelist()
def get_affiliate_cookie_timeout():
    return frappe.db.get_single_value("Affiliate Settings", "cookie_timeout") or 1


@frappe.whitelist()
def get_affiliate_settings():
    settings = frappe.get_single("Affiliate Settings")
    return {
        "cookie_timeout": settings.cookie_timeout or 1,
        "minimum_payout": settings.minimum_payout or 0,
        "delay_payout_days": settings.delay_payout_days or 0,
        "enable_keywords_support": settings.enable_keywords_support,
        "intro_text_on_affiliate_info_page": settings.intro_text_on_affiliate_info_page,
    }


@frappe.whitelist()
def get_banners_and_text_links(name=None, type_filter=None, category_filter=None):
    return_disabled = False
    if frappe.has_permission("Affiliate Settings", "write") is True:
        return_disabled = True
    user_groups = frappe.get_all(
        "User Group Member",
        filters={"user": frappe.session.user, "parenttype": "User Group"},
        pluck="parent",
    )

    affiliate_settings = frappe.get_single("Affiliate Settings")
    banners_text_links = []

    if hasattr(affiliate_settings, "banner_and_text_link"):
        for row in affiliate_settings.banner_and_text_link:
            if name and row.name != name:
                continue
            if type_filter and row.type != type_filter:
                continue
            if category_filter and row.category != category_filter:
                continue
            if (
                not category_filter
                and not return_disabled
                and (row.category != "" and row.category is not None)
            ):
                continue

            if not return_disabled and row.disabled:
                continue

            if not return_disabled:
                if user_groups:
                    if row.available_for_user_group not in user_groups + ["", None]:
                        continue
                else:
                    if row.available_for_user_group not in ["", None]:
                        continue

            banner_route_path = (
                frappe.get_single_value(
                    "Affiliate Settings", "banner_and_text_link_route_path"
                )
                or "/banner/"
            )

            row_data = {
                "name": row.name,
                "type": row.type,
                "banner": frappe.utils.get_url(
                    frappe.db.get_value("File", row.banner, "file_url")
                )
                if row.banner
                else "",
                "banner_name": frappe.db.get_value("File", row.banner, "name"),
                "redirect_url": row.redirect_url,
                "title": row.title,
                "description": row.description,
                "width": row.width,
                "height": row.height,
                "disabled": row.disabled,
                "category": row.category,
            }

            if return_disabled:
                row_data["available_for_user_group"] = row.available_for_user_group
                row_data["open_in_new_window"] = row.open_in_new_window
            else:
                affiliate_username = frappe.db.get_value(
                    "User", frappe.session.user, "username"
                )
                row_data["embed_url"] = frappe.utils.get_url(
                    banner_route_path + f"{row.name}/{affiliate_username}"
                )

            banners_text_links.append(row_data)

    return banners_text_links


@frappe.whitelist()
def get_banner_and_text_link_categories():
    return_disabled = False
    if frappe.has_permission("Affiliate Settings", "write") is True:
        return_disabled = True

    filters = {"disabled": 0, "category": ["is", "set"]}
    if not return_disabled:
        user_groups = frappe.get_all(
            "User Group Member",
            filters={"user": frappe.session.user, "parenttype": "User Group"},
            pluck="parent",
        )
        filters["available_for_user_group"] = ["in", user_groups + ["", None]]

    categories = frappe.get_all(
        "Affiliate Banner and Text Link",
        filters=filters,
        fields=["category", "available_for_user_group"],
        pluck="category",
    )
    return categories


@frappe.whitelist(methods=["POST"])
def update_banner_and_text_link(banner_id, **kwargs):
    """Update a specific banner and text link row in the child table"""
    affiliate_settings = frappe.get_single("Affiliate Settings")
    if hasattr(affiliate_settings, "banner_and_text_link"):
        for row in affiliate_settings.banner_and_text_link:
            if row.name == banner_id:
                for field, value in kwargs.items():
                    if hasattr(row, field):
                        setattr(row, field, value)

                affiliate_settings.save()
                return {"success": True, "message": "Banner updated successfully"}

        return {"success": False, "message": "Banner not found"}


def get_affiliate_marketing_materials():
    marketing_materials = frappe.get_all(
        "Affiliate Marketing Material",
        fields=["name", "material", "description"],
    )

    for material in marketing_materials:
        material["material_url"] = frappe.utils.get_url(material["material"])
        material["material_name"] = material["material"].split("/")[-1]
    return marketing_materials
