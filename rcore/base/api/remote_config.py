# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import Any, Optional
import frappe
from rcore.base.utils import get_subscription_details


@frappe.whitelist(allow_guest=True)
def get_remote_config(app_type: Any='Customer', site_name: Any=None) -> Any:
    """
    Fetches remote configuration for the Juvo Customer App directly from the tenant site.
    """
    # 1. Check Subscription Status
    try:
        # get_subscription_details calls the Control Panel to verify status
        sub_details = get_subscription_details()
        if sub_details.get("status") not in ["Active", "Trialing"]:
            frappe.throw("Subscription is not active.", title="Access Denied")

        # Optionally check for "paas" module in sub_details.get("modules")
        # if "paas" not in sub_details.get("modules", []):
        #    frappe.throw("This feature requires a PaaS subscription.")
    except Exception:
        frappe.log_error(
            frappe.get_traceback(), "Remote Config Subscription Check Failed"
        )
        frappe.throw("Could not verify subscription status.")

    # 2. Fetch Configuration Sources
    _current_site = frappe.local.site  # noqa: F841

    # A. Project Title from Settings
    project_title = frappe.db.get_single_value("Settings", "project_title")

    # B. Common Config
    common_config_name = frappe.db.get_value(
        "Remote Config", {"app_type": "Common"}, "name"
    )
    common_config = (
        frappe.get_doc("Remote Config", common_config_name)
        if common_config_name
        else None
    )

    # C. App Specific Config
    app_config_name = frappe.db.get_value(
        "Remote Config", {"app_type": app_type}, "name"
    )
    app_config = (
        frappe.get_doc("Remote Config", app_config_name)
        if app_config_name
        else None
    )

    if not common_config and not app_config:
        # Fallback: Check if config exists for "project_title" as site_name (legacy behavior?)
        # Or just return empty/defaults?
        # The user said "reading that project title".
        pass

    # 3. Merge and Map keys
    def get_val(field):
        val = None
        # Check app specific config first
        if app_config and getattr(app_config, field, None) is not None:
            if (
                isinstance(getattr(app_config, field), str)
                and getattr(app_config, field) == ""
            ):
                pass
            else:
                val = getattr(app_config, field)

        # Fallback to common config
        if (
            val is None
            and common_config
            and getattr(common_config, field, None) is not None
        ):
            if (
                isinstance(getattr(common_config, field), str)
                and getattr(common_config, field) == ""
            ):
                pass
            else:
                val = getattr(common_config, field)

        return val

    return {
        # --- Global Configuration (All Apps) ---
        "pinLoadingMin": get_val("pin_loading_min"),
        "pinLoadingMax": get_val("pin_loading_max"),
        # --- Auth & Localization (Customer, Driver, Manager) ---
        "isSpecificNumberEnabled": get_val("is_specific_number_enabled"),
        "isNumberLengthAlwaysSame": get_val("is_number_length_always_same"),
        "countryCodeISO": get_val("country_code_iso"),
        "showFlag": get_val("show_flag"),
        "showArrowIcon": get_val("show_arrow_icon"),
        "localeCodeEn": get_val("locale_code_en"),
        # --- Map & Navigation (Customer, Driver) ---
        "drawingBaseUrl": get_val("drawing_base_url"),
        "routingKey": get_val("routing_key"),
        "showGooglePOILayer": get_val("show_google_poi_layer"),
        "poiData": get_val("poi_data"),
        # --- Customer Specific ---
        "cardDirect": get_val("card_direct"),
        "newShopDays": get_val("new_shop_days"),
        "isOpen": get_val("is_open"),
        "isClosed": get_val("is_closed"),
        # --- POS & Manager Shared ---
        "chatGpt": get_val("chat_gpt"),
        "autoTrn": get_val("auto_trn"),
        # --- POS Specific ---
        "playMusicOnOrderStatusChange": get_val(
            "play_music_on_order_status_change"
        ),
        "keepPlayingOnNewOrder": get_val("keep_playing_on_new_order"),
        "refreshTime": get_val("refresh_time"),
        "animationDuration": get_val("animation_duration"),
        "weatherRefresher": get_val("weather_refresher"),
        "radius": get_val("radius"),
        "keyShopData": get_val("key_shop_data"),
        "autoDeliver": get_val("auto_deliver"),
        "secondScreen": get_val("second_screen"),
        "enableJuvoONE": get_val("enable_juvo_one"),
        "skipPin": get_val("skip_pin"),
        "useDummyDataFallback": get_val("use_dummy_data_fallback"),
        "enableOfflineMode": get_val("enable_offline_mode"),
        "sound": get_val("sound"),
        "idleTimeout": get_val("idle_timeout"),
        "fetchTime": get_val("fetch_time"),
        "dashboardFetchTime": get_val("dashboard_fetch_time"),
        "weatherIcon": get_val("weather_icon"),
        "rainPOP": get_val("rain_pop"),
        "dateAt": get_val("date_at"),
        "quickSaleNoUserStockIds": get_val("quick_sale_no_user_stock_ids"),
        "quickSaleDefaultQuantity": get_val("quick_sale_default_quantity"),
        "quickSaleCouponTapCount": get_val("quick_sale_coupon_tap_count"),
        "quickSaleStockId": get_val("quick_sale_stock_id"),
        "quickSaleCouponCode": get_val("quick_sale_coupon_code"),
        "maintenanceCheckDays": get_val("maintenance_check_days"),
        "preFilterReplaceDays": get_val("pre_filter_replace_days"),
        "postFilterReplaceDays": get_val("post_filter_replace_days"),
        "roFilterReplaceDays": get_val("ro_filter_replace_days"),
        "vesselReplaceDays": get_val("vessel_replace_days"),
        "roMembraneReplaceDays": get_val("ro_membrane_replace_days"),
        "megaCharMaintenanceDurations": get_val(
            "mega_char_maintenance_durations"
        ),
        "softenerMaintenanceDurations": get_val(
            "softener_maintenance_durations"
        ),
        "maintenanceTypes": get_val("maintenance_types"),
        "filterTypes": get_val("filter_types"),
        # --- Manager Specific ---
        "imageBaseUrl": get_val("image_base_url"),
        # Extras
        "projectTitle": project_title,
        "enableMarketplace": frappe.db.get_single_value(
            "Settings", "enable_marketplace"
        ),
        "defaultShopId": frappe.db.get_single_value(
            "Settings", "default_shop"
        ),
    }
