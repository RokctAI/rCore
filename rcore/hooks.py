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

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

app_name = "rcore"
app_title = "Rcore"
app_publisher = "ROKCT INTELLIGENCE (PTY) LTD"
app_description = "Core business logic and utilities"
app_email = "admin@rokct.ai"
app_license = "mit"

# NOTE: no required_apps = ["erpnext"] (unlike the retired paas shell).
# ERPNext-touching install/test steps are guarded at runtime with
# `"erpnext" in frappe.get_installed_apps()` instead.

# Testing
# -------
before_tests = "rcore.tests.utils.before_tests"

# Installation
# ------------
before_install = "rcore.install.check_site_role"
after_install = "rcore.install.after_install"
# before_uninstall for the build-in-progress guard is composed from the
# builder SDK module's manifest (corporate/builder/frappe) - not declared
# statically here, so it is registered exactly once.

# Website Route Rules
website_route_rules = [
    {
        "from_route": "/.well-known/assetlinks.json",
        "to_route": "rcore.api.app_links.get_assetlinks",
    },
    {
        "from_route": "/.well-known/apple-app-site-association",
        "to_route": "rcore.api.app_links.get_apple_app_site_association",
    },
]

# Whitelisted Methods (Public APIs)
whitelisted_methods = {
    # The single universal entry point for the platform (routes by site role)
    "rokct.platform.api": "rcore.platform.api.execute",
    # Legacy paas.* aliases kept for clients still calling the old app name.
    # Targets are the rcore-substituted paths the SDK module manifests declare.
    "paas.api.auth.refresh": "rcore.auth.api.auth.auth.refresh",
    "paas.tenant.api.log_frontend_error": "rcore.telemetry.telemetry.log_frontend_error.log_frontend_error",
    "paas.api.upload.upload_file": "rcore.base.api.upload.upload_file",
}

# Frappe's dispatcher resolves aliases from this hook (see frappe.override_whitelisted_method)
override_whitelisted_methods = {
    "rokct.platform.api": "rcore.platform.api.execute",
    "paas.api.auth.refresh": "rcore.auth.api.auth.auth.refresh",
    "paas.tenant.api.log_frontend_error": "rcore.telemetry.telemetry.log_frontend_error.log_frontend_error",
    "paas.api.upload.upload_file": "rcore.base.api.upload.upload_file",
}


# --- BEG OF DYNAMIC SDK HOOKS ---

# --- Module: base ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('daily', [])
for _t in ['rcore.base.core.tasks.check_invoice_payments', 'rcore.base.core.tasks.check_protocol_99_sequences', 'rcore.base.core.tasks.purge_expired_idempotency_keys']:
    if _t not in scheduler_events['daily']: scheduler_events['daily'].append(_t)
override_doctype_class = globals().get('override_doctype_class', {})
override_doctype_class['File'] = 'rcore.base.overrides.CustomFile'
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.system.get_global_settings'] = 'rcore.base.api.system.get_global_settings'
override_whitelisted_methods['rcore.api.system.get_global_settings'] = 'rcore.base.api.system.get_global_settings'
whitelisted_methods['rcore.api.translation.get_mobile_translations'] = 'rcore.base.api.translation.get_mobile_translations'
override_whitelisted_methods['rcore.api.translation.get_mobile_translations'] = 'rcore.base.api.translation.get_mobile_translations'
whitelisted_methods['rcore.api.system.get_policy'] = 'rcore.base.api.system.get_policy'
override_whitelisted_methods['rcore.api.system.get_policy'] = 'rcore.base.api.system.get_policy'
whitelisted_methods['rcore.api.system.get_terms'] = 'rcore.base.api.system.get_terms'
override_whitelisted_methods['rcore.api.system.get_terms'] = 'rcore.base.api.system.get_terms'
whitelisted_methods['rcore.api.payout.request_payout'] = 'rcore.merchants.api.payout.payout.request_payout'
override_whitelisted_methods['rcore.api.payout.request_payout'] = 'rcore.merchants.api.payout.payout.request_payout'
whitelisted_methods['rcore.api.upload.upload_multi_image'] = 'rcore.base.api.upload.upload_multi_image'
override_whitelisted_methods['rcore.api.upload.upload_multi_image'] = 'rcore.base.api.upload.upload_multi_image'
whitelisted_methods['rcore.api.admin_content.create_admin_banner'] = 'rcore.base.api.admin_content.create_admin_banner'
override_whitelisted_methods['rcore.api.admin_content.create_admin_banner'] = 'rcore.base.api.admin_content.create_admin_banner'
whitelisted_methods['rcore.api.admin_content.create_admin_faq'] = 'rcore.base.api.admin_content.create_admin_faq'
override_whitelisted_methods['rcore.api.admin_content.create_admin_faq'] = 'rcore.base.api.admin_content.create_admin_faq'
whitelisted_methods['rcore.api.admin_content.create_admin_faq_category'] = 'rcore.base.api.admin_content.create_admin_faq_category'
override_whitelisted_methods['rcore.api.admin_content.create_admin_faq_category'] = 'rcore.base.api.admin_content.create_admin_faq_category'
whitelisted_methods['rcore.api.admin_content.delete_admin_banner'] = 'rcore.base.api.admin_content.delete_admin_banner'
override_whitelisted_methods['rcore.api.admin_content.delete_admin_banner'] = 'rcore.base.api.admin_content.delete_admin_banner'
whitelisted_methods['rcore.api.admin_content.delete_admin_faq'] = 'rcore.base.api.admin_content.delete_admin_faq'
override_whitelisted_methods['rcore.api.admin_content.delete_admin_faq'] = 'rcore.base.api.admin_content.delete_admin_faq'
whitelisted_methods['rcore.api.admin_content.delete_admin_faq_category'] = 'rcore.base.api.admin_content.delete_admin_faq_category'
override_whitelisted_methods['rcore.api.admin_content.delete_admin_faq_category'] = 'rcore.base.api.admin_content.delete_admin_faq_category'
whitelisted_methods['rcore.api.admin_content.get_admin_banners'] = 'rcore.base.api.admin_content.get_admin_banners'
override_whitelisted_methods['rcore.api.admin_content.get_admin_banners'] = 'rcore.base.api.admin_content.get_admin_banners'
whitelisted_methods['rcore.api.admin_content.get_admin_faq_categories'] = 'rcore.base.api.admin_content.get_admin_faq_categories'
override_whitelisted_methods['rcore.api.admin_content.get_admin_faq_categories'] = 'rcore.base.api.admin_content.get_admin_faq_categories'
whitelisted_methods['rcore.api.admin_content.get_admin_faqs'] = 'rcore.base.api.admin_content.get_admin_faqs'
override_whitelisted_methods['rcore.api.admin_content.get_admin_faqs'] = 'rcore.base.api.admin_content.get_admin_faqs'
whitelisted_methods['rcore.api.admin_content.get_admin_stories'] = 'rcore.base.api.admin_content.get_admin_stories'
override_whitelisted_methods['rcore.api.admin_content.get_admin_stories'] = 'rcore.base.api.admin_content.get_admin_stories'
whitelisted_methods['rcore.api.admin_content.update_admin_banner'] = 'rcore.base.api.admin_content.update_admin_banner'
override_whitelisted_methods['rcore.api.admin_content.update_admin_banner'] = 'rcore.base.api.admin_content.update_admin_banner'
whitelisted_methods['rcore.api.admin_content.update_admin_faq'] = 'rcore.base.api.admin_content.update_admin_faq'
override_whitelisted_methods['rcore.api.admin_content.update_admin_faq'] = 'rcore.base.api.admin_content.update_admin_faq'
whitelisted_methods['rcore.api.admin_content.update_admin_faq_category'] = 'rcore.base.api.admin_content.update_admin_faq_category'
override_whitelisted_methods['rcore.api.admin_content.update_admin_faq_category'] = 'rcore.base.api.admin_content.update_admin_faq_category'
whitelisted_methods['rcore.api.admin_data.create_point'] = 'rcore.base.api.admin_data.create_point'
override_whitelisted_methods['rcore.api.admin_data.create_point'] = 'rcore.base.api.admin_data.create_point'
whitelisted_methods['rcore.api.admin_data.create_referral'] = 'rcore.base.api.admin_data.create_referral'
override_whitelisted_methods['rcore.api.admin_data.create_referral'] = 'rcore.base.api.admin_data.create_referral'
whitelisted_methods['rcore.api.admin_data.delete_point'] = 'rcore.base.api.admin_data.delete_point'
override_whitelisted_methods['rcore.api.admin_data.delete_point'] = 'rcore.base.api.admin_data.delete_point'
whitelisted_methods['rcore.api.admin_data.delete_referral'] = 'rcore.base.api.admin_data.delete_referral'
override_whitelisted_methods['rcore.api.admin_data.delete_referral'] = 'rcore.base.api.admin_data.delete_referral'
whitelisted_methods['rcore.api.admin_data.get_all_points'] = 'rcore.base.api.admin_data.get_all_points'
override_whitelisted_methods['rcore.api.admin_data.get_all_points'] = 'rcore.base.api.admin_data.get_all_points'
whitelisted_methods['rcore.api.admin_data.get_all_product_extra_groups'] = 'rcore.base.api.admin_data.get_all_product_extra_groups'
override_whitelisted_methods['rcore.api.admin_data.get_all_product_extra_groups'] = 'rcore.base.api.admin_data.get_all_product_extra_groups'
whitelisted_methods['rcore.api.admin_data.get_all_product_extra_values'] = 'rcore.base.api.admin_data.get_all_product_extra_values'
override_whitelisted_methods['rcore.api.admin_data.get_all_product_extra_values'] = 'rcore.base.api.admin_data.get_all_product_extra_values'
whitelisted_methods['rcore.api.admin_data.get_all_referrals'] = 'rcore.base.api.admin_data.get_all_referrals'
override_whitelisted_methods['rcore.api.admin_data.get_all_referrals'] = 'rcore.base.api.admin_data.get_all_referrals'
whitelisted_methods['rcore.api.admin_data.get_all_shop_tags'] = 'rcore.base.api.admin_data.get_all_shop_tags'
override_whitelisted_methods['rcore.api.admin_data.get_all_shop_tags'] = 'rcore.base.api.admin_data.get_all_shop_tags'
whitelisted_methods['rcore.api.admin_data.get_all_tags'] = 'rcore.base.api.admin_data.get_all_tags'
override_whitelisted_methods['rcore.api.admin_data.get_all_tags'] = 'rcore.base.api.admin_data.get_all_tags'
whitelisted_methods['rcore.api.admin_data.get_all_translations'] = 'rcore.base.api.admin_data.get_all_translations'
override_whitelisted_methods['rcore.api.admin_data.get_all_translations'] = 'rcore.base.api.admin_data.get_all_translations'
whitelisted_methods['rcore.api.admin_data.get_all_units'] = 'rcore.base.api.admin_data.get_all_units'
override_whitelisted_methods['rcore.api.admin_data.get_all_units'] = 'rcore.base.api.admin_data.get_all_units'
whitelisted_methods['rcore.api.admin_data.update_point'] = 'rcore.base.api.admin_data.update_point'
override_whitelisted_methods['rcore.api.admin_data.update_point'] = 'rcore.base.api.admin_data.update_point'
whitelisted_methods['rcore.api.admin_logistics.create_delivery_vehicle_type'] = 'rcore.base.api.admin_logistics.create_delivery_vehicle_type'
override_whitelisted_methods['rcore.api.admin_logistics.create_delivery_vehicle_type'] = 'rcore.base.api.admin_logistics.create_delivery_vehicle_type'
whitelisted_methods['rcore.api.admin_logistics.create_parcel_order_setting'] = 'rcore.base.api.admin_logistics.create_parcel_order_setting'
override_whitelisted_methods['rcore.api.admin_logistics.create_parcel_order_setting'] = 'rcore.base.api.admin_logistics.create_parcel_order_setting'
whitelisted_methods['rcore.api.admin_logistics.delete_delivery_vehicle_type'] = 'rcore.base.api.admin_logistics.delete_delivery_vehicle_type'
override_whitelisted_methods['rcore.api.admin_logistics.delete_delivery_vehicle_type'] = 'rcore.base.api.admin_logistics.delete_delivery_vehicle_type'
whitelisted_methods['rcore.api.admin_logistics.delete_parcel_order_setting'] = 'rcore.base.api.admin_logistics.delete_parcel_order_setting'
override_whitelisted_methods['rcore.api.admin_logistics.delete_parcel_order_setting'] = 'rcore.base.api.admin_logistics.delete_parcel_order_setting'
whitelisted_methods['rcore.api.admin_logistics.get_all_delivery_man_delivery_zones'] = 'rcore.base.api.admin_logistics.get_all_delivery_man_delivery_zones'
override_whitelisted_methods['rcore.api.admin_logistics.get_all_delivery_man_delivery_zones'] = 'rcore.base.api.admin_logistics.get_all_delivery_man_delivery_zones'
whitelisted_methods['rcore.api.admin_logistics.get_all_delivery_zones'] = 'rcore.base.api.admin_logistics.get_all_delivery_zones'
override_whitelisted_methods['rcore.api.admin_logistics.get_all_delivery_zones'] = 'rcore.base.api.admin_logistics.get_all_delivery_zones'
whitelisted_methods['rcore.api.admin_logistics.get_all_shop_closed_days'] = 'rcore.base.api.admin_logistics.get_all_shop_closed_days'
override_whitelisted_methods['rcore.api.admin_logistics.get_all_shop_closed_days'] = 'rcore.base.api.admin_logistics.get_all_shop_closed_days'
whitelisted_methods['rcore.api.admin_logistics.get_all_shop_working_days'] = 'rcore.base.api.admin_logistics.get_all_shop_working_days'
override_whitelisted_methods['rcore.api.admin_logistics.get_all_shop_working_days'] = 'rcore.base.api.admin_logistics.get_all_shop_working_days'
whitelisted_methods['rcore.api.admin_logistics.get_delivery_vehicle_types'] = 'rcore.base.api.admin_logistics.get_delivery_vehicle_types'
override_whitelisted_methods['rcore.api.admin_logistics.get_delivery_vehicle_types'] = 'rcore.base.api.admin_logistics.get_delivery_vehicle_types'
whitelisted_methods['rcore.api.admin_logistics.get_deliveryman_global_settings'] = 'rcore.base.api.admin_logistics.get_deliveryman_global_settings'
override_whitelisted_methods['rcore.api.admin_logistics.get_deliveryman_global_settings'] = 'rcore.base.api.admin_logistics.get_deliveryman_global_settings'
whitelisted_methods['rcore.api.admin_logistics.get_parcel_order_settings'] = 'rcore.base.api.admin_logistics.get_parcel_order_settings'
override_whitelisted_methods['rcore.api.admin_logistics.get_parcel_order_settings'] = 'rcore.base.api.admin_logistics.get_parcel_order_settings'
whitelisted_methods['rcore.api.admin_logistics.update_delivery_vehicle_type'] = 'rcore.base.api.admin_logistics.update_delivery_vehicle_type'
override_whitelisted_methods['rcore.api.admin_logistics.update_delivery_vehicle_type'] = 'rcore.base.api.admin_logistics.update_delivery_vehicle_type'
whitelisted_methods['rcore.api.admin_logistics.update_deliveryman_global_settings'] = 'rcore.base.api.admin_logistics.update_deliveryman_global_settings'
override_whitelisted_methods['rcore.api.admin_logistics.update_deliveryman_global_settings'] = 'rcore.base.api.admin_logistics.update_deliveryman_global_settings'
whitelisted_methods['rcore.api.admin_logistics.update_parcel_order_setting'] = 'rcore.base.api.admin_logistics.update_parcel_order_setting'
override_whitelisted_methods['rcore.api.admin_logistics.update_parcel_order_setting'] = 'rcore.base.api.admin_logistics.update_parcel_order_setting'
whitelisted_methods['rcore.api.admin_management.create_shop'] = 'rcore.base.api.admin_management.create_shop'
override_whitelisted_methods['rcore.api.admin_management.create_shop'] = 'rcore.base.api.admin_management.create_shop'
whitelisted_methods['rcore.api.admin_management.delete_shop'] = 'rcore.base.api.admin_management.delete_shop'
override_whitelisted_methods['rcore.api.admin_management.delete_shop'] = 'rcore.base.api.admin_management.delete_shop'
whitelisted_methods['rcore.api.admin_management.get_all_roles'] = 'rcore.base.api.admin_management.get_all_roles'
override_whitelisted_methods['rcore.api.admin_management.get_all_roles'] = 'rcore.base.api.admin_management.get_all_roles'
whitelisted_methods['rcore.api.admin_management.get_all_shops'] = 'rcore.base.api.admin_management.get_all_shops'
override_whitelisted_methods['rcore.api.admin_management.get_all_shops'] = 'rcore.base.api.admin_management.get_all_shops'
whitelisted_methods['rcore.api.admin_management.get_all_users'] = 'rcore.base.api.admin_management.get_all_users'
override_whitelisted_methods['rcore.api.admin_management.get_all_users'] = 'rcore.base.api.admin_management.get_all_users'
whitelisted_methods['rcore.api.admin_management.update_shop'] = 'rcore.base.api.admin_management.update_shop'
override_whitelisted_methods['rcore.api.admin_management.update_shop'] = 'rcore.base.api.admin_management.update_shop'
whitelisted_methods['rcore.api.admin_records.assign_deliveryman_to_parcel'] = 'rcore.base.api.admin_records.assign_deliveryman_to_parcel'
override_whitelisted_methods['rcore.api.admin_records.assign_deliveryman_to_parcel'] = 'rcore.base.api.admin_records.assign_deliveryman_to_parcel'
whitelisted_methods['rcore.api.admin_records.create_booking'] = 'rcore.base.api.admin_records.create_booking'
override_whitelisted_methods['rcore.api.admin_records.create_booking'] = 'rcore.base.api.admin_records.create_booking'
whitelisted_methods['rcore.api.admin_records.delete_admin_parcel_order'] = 'rcore.base.api.admin_records.delete_admin_parcel_order'
override_whitelisted_methods['rcore.api.admin_records.delete_admin_parcel_order'] = 'rcore.base.api.admin_records.delete_admin_parcel_order'
whitelisted_methods['rcore.api.admin_records.delete_admin_review'] = 'rcore.base.api.admin_records.delete_admin_review'
override_whitelisted_methods['rcore.api.admin_records.delete_admin_review'] = 'rcore.base.api.admin_records.delete_admin_review'
whitelisted_methods['rcore.api.admin_records.delete_booking'] = 'rcore.base.api.admin_records.delete_booking'
override_whitelisted_methods['rcore.api.admin_records.delete_booking'] = 'rcore.base.api.admin_records.delete_booking'
whitelisted_methods['rcore.api.admin_records.get_all_bookings'] = 'rcore.base.api.admin_records.get_all_bookings'
override_whitelisted_methods['rcore.api.admin_records.get_all_bookings'] = 'rcore.base.api.admin_records.get_all_bookings'
whitelisted_methods['rcore.api.admin_records.get_all_notifications'] = 'rcore.base.api.admin_records.get_all_notifications'
override_whitelisted_methods['rcore.api.admin_records.get_all_notifications'] = 'rcore.base.api.admin_records.get_all_notifications'
whitelisted_methods['rcore.api.admin_records.get_all_order_refunds'] = 'rcore.base.api.admin_records.get_all_order_refunds'
override_whitelisted_methods['rcore.api.admin_records.get_all_order_refunds'] = 'rcore.base.api.admin_records.get_all_order_refunds'
whitelisted_methods['rcore.api.admin_records.get_all_order_statuses'] = 'rcore.base.api.admin_records.get_all_order_statuses'
override_whitelisted_methods['rcore.api.admin_records.get_all_order_statuses'] = 'rcore.base.api.admin_records.get_all_order_statuses'
whitelisted_methods['rcore.api.admin_records.get_all_orders'] = 'rcore.base.api.admin_records.get_all_orders'
override_whitelisted_methods['rcore.api.admin_records.get_all_orders'] = 'rcore.base.api.admin_records.get_all_orders'
whitelisted_methods['rcore.api.admin_records.get_all_parcel_orders'] = 'rcore.base.api.admin_records.get_all_parcel_orders'
override_whitelisted_methods['rcore.api.admin_records.get_all_parcel_orders'] = 'rcore.base.api.admin_records.get_all_parcel_orders'
whitelisted_methods['rcore.api.admin_records.get_all_request_models'] = 'rcore.base.api.admin_records.get_all_request_models'
override_whitelisted_methods['rcore.api.admin_records.get_all_request_models'] = 'rcore.base.api.admin_records.get_all_request_models'
whitelisted_methods['rcore.api.admin_records.get_all_reviews'] = 'rcore.base.api.admin_records.get_all_reviews'
override_whitelisted_methods['rcore.api.admin_records.get_all_reviews'] = 'rcore.base.api.admin_records.get_all_reviews'
whitelisted_methods['rcore.api.admin_records.get_all_tickets'] = 'rcore.base.api.admin_records.get_all_tickets'
override_whitelisted_methods['rcore.api.admin_records.get_all_tickets'] = 'rcore.base.api.admin_records.get_all_tickets'
whitelisted_methods['rcore.api.admin_records.update_admin_order_refund'] = 'rcore.base.api.admin_records.update_admin_order_refund'
override_whitelisted_methods['rcore.api.admin_records.update_admin_order_refund'] = 'rcore.base.api.admin_records.update_admin_order_refund'
whitelisted_methods['rcore.api.admin_records.update_admin_review'] = 'rcore.base.api.admin_records.update_admin_review'
override_whitelisted_methods['rcore.api.admin_records.update_admin_review'] = 'rcore.base.api.admin_records.update_admin_review'
whitelisted_methods['rcore.api.admin_records.update_admin_ticket'] = 'rcore.base.api.admin_records.update_admin_ticket'
override_whitelisted_methods['rcore.api.admin_records.update_admin_ticket'] = 'rcore.base.api.admin_records.update_admin_ticket'
whitelisted_methods['rcore.api.admin_records.update_booking'] = 'rcore.base.api.admin_records.update_booking'
override_whitelisted_methods['rcore.api.admin_records.update_booking'] = 'rcore.base.api.admin_records.update_booking'
whitelisted_methods['rcore.api.admin_reports.get_admin_report'] = 'rcore.base.api.admin_reports.get_admin_report'
override_whitelisted_methods['rcore.api.admin_reports.get_admin_report'] = 'rcore.base.api.admin_reports.get_admin_report'
whitelisted_methods['rcore.api.admin_reports.get_admin_statistics'] = 'rcore.base.api.admin_reports.get_admin_statistics'
override_whitelisted_methods['rcore.api.admin_reports.get_admin_statistics'] = 'rcore.base.api.admin_reports.get_admin_statistics'
whitelisted_methods['rcore.api.admin_reports.get_all_seller_payouts'] = 'rcore.base.api.admin_reports.get_all_seller_payouts'
override_whitelisted_methods['rcore.api.admin_reports.get_all_seller_payouts'] = 'rcore.base.api.admin_reports.get_all_seller_payouts'
whitelisted_methods['rcore.api.admin_reports.get_all_shop_bonuses'] = 'rcore.base.api.admin_reports.get_all_shop_bonuses'
override_whitelisted_methods['rcore.api.admin_reports.get_all_shop_bonuses'] = 'rcore.base.api.admin_reports.get_all_shop_bonuses'
whitelisted_methods['rcore.api.admin_reports.get_all_transactions'] = 'rcore.base.api.admin_reports.get_all_transactions'
override_whitelisted_methods['rcore.api.admin_reports.get_all_transactions'] = 'rcore.base.api.admin_reports.get_all_transactions'
whitelisted_methods['rcore.api.admin_reports.get_all_wallet_histories'] = 'rcore.base.api.admin_reports.get_all_wallet_histories'
override_whitelisted_methods['rcore.api.admin_reports.get_all_wallet_histories'] = 'rcore.base.api.admin_reports.get_all_wallet_histories'
whitelisted_methods['rcore.api.admin_reports.get_multi_company_sales_report'] = 'rcore.base.api.admin_reports.get_multi_company_sales_report'
override_whitelisted_methods['rcore.api.admin_reports.get_multi_company_sales_report'] = 'rcore.base.api.admin_reports.get_multi_company_sales_report'
whitelisted_methods['rcore.api.admin_settings.create_email_subscription'] = 'rcore.base.api.admin_settings.create_email_subscription'
override_whitelisted_methods['rcore.api.admin_settings.create_email_subscription'] = 'rcore.base.api.admin_settings.create_email_subscription'
whitelisted_methods['rcore.api.admin_settings.delete_email_subscription'] = 'rcore.base.api.admin_settings.delete_email_subscription'
override_whitelisted_methods['rcore.api.admin_settings.delete_email_subscription'] = 'rcore.base.api.admin_settings.delete_email_subscription'
whitelisted_methods['rcore.api.admin_settings.get_all_currencies'] = 'rcore.base.api.admin_settings.get_all_currencies'
override_whitelisted_methods['rcore.api.admin_settings.get_all_currencies'] = 'rcore.base.api.admin_settings.get_all_currencies'
whitelisted_methods['rcore.api.admin_settings.get_all_email_templates'] = 'rcore.base.api.admin_settings.get_all_email_templates'
override_whitelisted_methods['rcore.api.admin_settings.get_all_email_templates'] = 'rcore.base.api.admin_settings.get_all_email_templates'
whitelisted_methods['rcore.api.admin_settings.get_all_languages'] = 'rcore.base.api.admin_settings.get_all_languages'
override_whitelisted_methods['rcore.api.admin_settings.get_all_languages'] = 'rcore.base.api.admin_settings.get_all_languages'
whitelisted_methods['rcore.api.admin_settings.get_app_settings'] = 'rcore.base.api.admin_settings.get_app_settings'
override_whitelisted_methods['rcore.api.admin_settings.get_app_settings'] = 'rcore.base.api.admin_settings.get_app_settings'
whitelisted_methods['rcore.api.admin_settings.get_email_settings'] = 'rcore.base.api.admin_settings.get_email_settings'
override_whitelisted_methods['rcore.api.admin_settings.get_email_settings'] = 'rcore.base.api.admin_settings.get_email_settings'
whitelisted_methods['rcore.api.admin_settings.get_email_subscriptions'] = 'rcore.base.api.admin_settings.get_email_subscriptions'
override_whitelisted_methods['rcore.api.admin_settings.get_email_subscriptions'] = 'rcore.base.api.admin_settings.get_email_subscriptions'
whitelisted_methods['rcore.api.admin_settings.get_general_settings'] = 'rcore.base.api.admin_settings.get_general_settings'
override_whitelisted_methods['rcore.api.admin_settings.get_general_settings'] = 'rcore.base.api.admin_settings.get_general_settings'
whitelisted_methods['rcore.api.admin_settings.update_app_settings'] = 'rcore.base.api.admin_settings.update_app_settings'
override_whitelisted_methods['rcore.api.admin_settings.update_app_settings'] = 'rcore.base.api.admin_settings.update_app_settings'
whitelisted_methods['rcore.api.admin_settings.update_currency'] = 'rcore.base.api.admin_settings.update_currency'
override_whitelisted_methods['rcore.api.admin_settings.update_currency'] = 'rcore.base.api.admin_settings.update_currency'
whitelisted_methods['rcore.api.admin_settings.update_email_settings'] = 'rcore.base.api.admin_settings.update_email_settings'
override_whitelisted_methods['rcore.api.admin_settings.update_email_settings'] = 'rcore.base.api.admin_settings.update_email_settings'
whitelisted_methods['rcore.api.admin_settings.update_email_template'] = 'rcore.base.api.admin_settings.update_email_template'
override_whitelisted_methods['rcore.api.admin_settings.update_email_template'] = 'rcore.base.api.admin_settings.update_email_template'
whitelisted_methods['rcore.api.admin_settings.update_general_settings'] = 'rcore.base.api.admin_settings.update_general_settings'
override_whitelisted_methods['rcore.api.admin_settings.update_general_settings'] = 'rcore.base.api.admin_settings.update_general_settings'
whitelisted_methods['rcore.api.admin_settings.update_language'] = 'rcore.base.api.admin_settings.update_language'
override_whitelisted_methods['rcore.api.admin_settings.update_language'] = 'rcore.base.api.admin_settings.update_language'
whitelisted_methods['rcore.api.admin_system.clear_system_cache'] = 'rcore.base.api.admin_system.clear_system_cache'
override_whitelisted_methods['rcore.api.admin_system.clear_system_cache'] = 'rcore.base.api.admin_system.clear_system_cache'
whitelisted_methods['rcore.api.admin_system.create_backup'] = 'rcore.base.api.admin_system.create_backup'
override_whitelisted_methods['rcore.api.admin_system.create_backup'] = 'rcore.base.api.admin_system.create_backup'
whitelisted_methods['rcore.api.admin_system.get_backups'] = 'rcore.base.api.admin_system.get_backups'
override_whitelisted_methods['rcore.api.admin_system.get_backups'] = 'rcore.base.api.admin_system.get_backups'
whitelisted_methods['rcore.api.admin_system.get_system_info'] = 'rcore.base.api.admin_system.get_system_info'
override_whitelisted_methods['rcore.api.admin_system.get_system_info'] = 'rcore.base.api.admin_system.get_system_info'
whitelisted_methods['rcore.api.app_links.get_apple_app_site_association'] = 'rcore.base.api.app_links.get_apple_app_site_association'
override_whitelisted_methods['rcore.api.app_links.get_apple_app_site_association'] = 'rcore.base.api.app_links.get_apple_app_site_association'
whitelisted_methods['rcore.api.app_links.get_assetlinks'] = 'rcore.base.api.app_links.get_assetlinks'
override_whitelisted_methods['rcore.api.app_links.get_assetlinks'] = 'rcore.base.api.app_links.get_assetlinks'
whitelisted_methods['rcore.api.branch.create_branch'] = 'rcore.base.api.branch.create_branch'
override_whitelisted_methods['rcore.api.branch.create_branch'] = 'rcore.base.api.branch.create_branch'
whitelisted_methods['rcore.api.branch.delete_branch'] = 'rcore.base.api.branch.delete_branch'
override_whitelisted_methods['rcore.api.branch.delete_branch'] = 'rcore.base.api.branch.delete_branch'
whitelisted_methods['rcore.api.branch.get_branch'] = 'rcore.base.api.branch.get_branch'
override_whitelisted_methods['rcore.api.branch.get_branch'] = 'rcore.base.api.branch.get_branch'
whitelisted_methods['rcore.api.branch.get_branches'] = 'rcore.base.api.branch.get_branches'
override_whitelisted_methods['rcore.api.branch.get_branches'] = 'rcore.base.api.branch.get_branches'
whitelisted_methods['rcore.api.branch.update_branch'] = 'rcore.base.api.branch.update_branch'
override_whitelisted_methods['rcore.api.branch.update_branch'] = 'rcore.base.api.branch.update_branch'
whitelisted_methods['rcore.api.language.get_default_language'] = 'rcore.base.api.language.get_default_language'
override_whitelisted_methods['rcore.api.language.get_default_language'] = 'rcore.base.api.language.get_default_language'
whitelisted_methods['rcore.api.language.get_languages'] = 'rcore.base.api.language.get_languages'
override_whitelisted_methods['rcore.api.language.get_languages'] = 'rcore.base.api.language.get_languages'
whitelisted_methods['rcore.api.language.get_translations'] = 'rcore.base.api.language.get_translations'
override_whitelisted_methods['rcore.api.language.get_translations'] = 'rcore.base.api.language.get_translations'
whitelisted_methods['rcore.api.page.get_admin_pages'] = 'rcore.base.api.page.get_admin_pages'
override_whitelisted_methods['rcore.api.page.get_admin_pages'] = 'rcore.base.api.page.get_admin_pages'
whitelisted_methods['rcore.api.page.get_admin_web_page'] = 'rcore.base.api.page.get_admin_web_page'
override_whitelisted_methods['rcore.api.page.get_admin_web_page'] = 'rcore.base.api.page.get_admin_web_page'
whitelisted_methods['rcore.api.page.get_page'] = 'rcore.base.api.page.get_page'
override_whitelisted_methods['rcore.api.page.get_page'] = 'rcore.base.api.page.get_page'
whitelisted_methods['rcore.api.page.update_admin_web_page'] = 'rcore.base.api.page.update_admin_web_page'
override_whitelisted_methods['rcore.api.page.update_admin_web_page'] = 'rcore.base.api.page.update_admin_web_page'
whitelisted_methods['rcore.api.remote_config.get_remote_config'] = 'rcore.base.api.remote_config.get_remote_config'
override_whitelisted_methods['rcore.api.remote_config.get_remote_config'] = 'rcore.base.api.remote_config.get_remote_config'
whitelisted_methods['rcore.api.system.api_status'] = 'rcore.base.api.system.api_status'
override_whitelisted_methods['rcore.api.system.api_status'] = 'rcore.base.api.system.api_status'
whitelisted_methods['rcore.api.system.get_currencies'] = 'rcore.base.api.system.get_currencies'
override_whitelisted_methods['rcore.api.system.get_currencies'] = 'rcore.base.api.system.get_currencies'
whitelisted_methods['rcore.api.system.get_languages'] = 'rcore.base.api.system.get_languages'
override_whitelisted_methods['rcore.api.system.get_languages'] = 'rcore.base.api.system.get_languages'
whitelisted_methods['rcore.api.system.get_weather'] = 'rcore.base.api.system.get_weather'
override_whitelisted_methods['rcore.api.system.get_weather'] = 'rcore.base.api.system.get_weather'
whitelisted_methods['rcore.api.system.trigger_system_update'] = 'rcore.base.api.system.trigger_system_update'
override_whitelisted_methods['rcore.api.system.trigger_system_update'] = 'rcore.base.api.system.trigger_system_update'
whitelisted_methods['rcore.api.translation.create_translation'] = 'rcore.base.api.translation.create_translation'
override_whitelisted_methods['rcore.api.translation.create_translation'] = 'rcore.base.api.translation.create_translation'
whitelisted_methods['rcore.api.translation.delete_translation'] = 'rcore.base.api.translation.delete_translation'
override_whitelisted_methods['rcore.api.translation.delete_translation'] = 'rcore.base.api.translation.delete_translation'
whitelisted_methods['rcore.api.translation.drop_all_translations'] = 'rcore.base.api.translation.drop_all_translations'
override_whitelisted_methods['rcore.api.translation.drop_all_translations'] = 'rcore.base.api.translation.drop_all_translations'
whitelisted_methods['rcore.api.translation.export_translations'] = 'rcore.base.api.translation.export_translations'
override_whitelisted_methods['rcore.api.translation.export_translations'] = 'rcore.base.api.translation.export_translations'
whitelisted_methods['rcore.api.translation.get_translations_paginate'] = 'rcore.base.api.translation.get_translations_paginate'
override_whitelisted_methods['rcore.api.translation.get_translations_paginate'] = 'rcore.base.api.translation.get_translations_paginate'
whitelisted_methods['rcore.api.translation.import_translations'] = 'rcore.base.api.translation.import_translations'
override_whitelisted_methods['rcore.api.translation.import_translations'] = 'rcore.base.api.translation.import_translations'
whitelisted_methods['rcore.api.translation.restore_all_translations'] = 'rcore.base.api.translation.restore_all_translations'
override_whitelisted_methods['rcore.api.translation.restore_all_translations'] = 'rcore.base.api.translation.restore_all_translations'
whitelisted_methods['rcore.api.translation.truncate_translations'] = 'rcore.base.api.translation.truncate_translations'
override_whitelisted_methods['rcore.api.translation.truncate_translations'] = 'rcore.base.api.translation.truncate_translations'
whitelisted_methods['rcore.api.translation.update_translation'] = 'rcore.base.api.translation.update_translation'
override_whitelisted_methods['rcore.api.translation.update_translation'] = 'rcore.base.api.translation.update_translation'
whitelisted_methods['rcore.api.upload.upload_file'] = 'rcore.base.api.upload.upload_file'
override_whitelisted_methods['rcore.api.upload.upload_file'] = 'rcore.base.api.upload.upload_file'
whitelisted_methods['rcore.tenant.api.initial_setup'] = 'rcore.base.core.initial_setup.initial_setup'
override_whitelisted_methods['rcore.tenant.api.initial_setup'] = 'rcore.base.core.initial_setup.initial_setup'
whitelisted_methods['rcore.tenant.api.complete_onboarding'] = 'rcore.base.core.complete_onboarding.complete_onboarding'
override_whitelisted_methods['rcore.tenant.api.complete_onboarding'] = 'rcore.base.core.complete_onboarding.complete_onboarding'
whitelisted_methods['rcore.tenant.api.update_fiscal_year_if_default'] = 'rcore.base.core.update_fiscal_year_if_default.update_fiscal_year_if_default'
override_whitelisted_methods['rcore.tenant.api.update_fiscal_year_if_default'] = 'rcore.base.core.update_fiscal_year_if_default.update_fiscal_year_if_default'
whitelisted_methods['rcore.tenant.api.create_sales_invoice'] = 'rcore.base.core.create_sales_invoice.create_sales_invoice'
override_whitelisted_methods['rcore.tenant.api.create_sales_invoice'] = 'rcore.base.core.create_sales_invoice.create_sales_invoice'
whitelisted_methods['rcore.tenant.api.set_platform_secret'] = 'rcore.base.core.set_platform_secret.set_platform_secret'
override_whitelisted_methods['rcore.tenant.api.set_platform_secret'] = 'rcore.base.core.set_platform_secret.set_platform_secret'
whitelisted_methods['rcore.tenant.api.announce_ready_to_control'] = 'rcore.base.core.announce_ready_to_control.announce_ready_to_control'
override_whitelisted_methods['rcore.tenant.api.announce_ready_to_control'] = 'rcore.base.core.announce_ready_to_control.announce_ready_to_control'
whitelisted_methods['rcore.api.setup.update_naming_series.update_naming_series'] = 'rcore.base.setup.update_naming_series.update_naming_series'
override_whitelisted_methods['rcore.api.setup.update_naming_series.update_naming_series'] = 'rcore.base.setup.update_naming_series.update_naming_series'
doc_events = globals().get('doc_events', {})
doc_events.setdefault('Company', {})
_ev = doc_events['Company'].get('before_insert') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.base.core.company_guard.company_guard.block_second_company']:
    if _h not in _ev: _ev.append(_h)
doc_events['Company']['before_insert'] = _ev
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Idempotency Key']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Kitchen Translation']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Subscription']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Parcel Order Item']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Parcel Category']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Parcel Option']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Ads Package']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Membership']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Booking Closed Date']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Wallet History']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Cart']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Coupon Translation']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Point']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Order Item']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'User Shop']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Seller Payout']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Unit']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Ads Package']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Booking Working Day']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Branch']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Gallery']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Delivery Vehicle Type']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Deliveryman Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Menu Item']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Loan Contract']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Product Extra Value']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Closed Day']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Cart User']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Delivery Point']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Subscription']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Working Day']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Category']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'FAQ Category']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Tag']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'User Booking']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Category Translation']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'DeliveryMan Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Section']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Ticket']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Deliveryman Delivery Zone']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Coupon Usage']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Flutterwave Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Email Subscription']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Ban']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'User Membership']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Payment Payload']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Parcel Order Setting']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Product Translation']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Bonus']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Cashback Rule']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Combo Item']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Permission Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Project Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Email Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Request Model']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'FAQ']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Invitation']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Product Extra Group']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Tag']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Order Refund']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Loan Application']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Global Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Parcel Review']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Loan Eligibility Check']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Cart User']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Eligible Plan']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Career Category']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Career']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Delivery Zone Coordinate']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Order Status']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Receipt Stock']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Receipt Instruction']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Receipt Ingredient']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Receipt Nutrition']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'User Cart']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Cart Detail']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'PaaS Translation']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Referral Campaign']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Referral Campaign Translation']]})
fixtures.append({'dt': 'Province'})
fixtures.append({'dt': 'Organ of State'})
fixtures.append({'dt': 'Custom Field', 'filters': [['fieldname', 'in', ['login_redirect', 'item_is_visible']]]})
fixtures.append({'dt': 'Custom DocPerm', 'filters': [['parent', 'in', ['Company', 'Sales Invoice']]]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Legacy Vault']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Legacy Relationship']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Obituary Draft']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Life Event']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Province']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Organ of State']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Location Type']]})

# --- Module: auth ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.auth.refresh'] = 'rcore.auth.api.auth.auth.refresh'
override_whitelisted_methods['rcore.api.auth.refresh'] = 'rcore.auth.api.auth.auth.refresh'
whitelisted_methods['rcore.tenant.api.verify_my_email'] = 'rcore.auth.auth.verify_my_email.verify_my_email'
override_whitelisted_methods['rcore.tenant.api.verify_my_email'] = 'rcore.auth.auth.verify_my_email.verify_my_email'
whitelisted_methods['rcore.tenant.api.resend_verification_email'] = 'rcore.auth.auth.resend_verification_email.resend_verification_email'
override_whitelisted_methods['rcore.tenant.api.resend_verification_email'] = 'rcore.auth.auth.resend_verification_email.resend_verification_email'
whitelisted_methods['rcore.tenant.api.update_verification_token'] = 'rcore.auth.auth.update_verification_token.update_verification_token'
override_whitelisted_methods['rcore.tenant.api.update_verification_token'] = 'rcore.auth.auth.update_verification_token.update_verification_token'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Password Reset']]})
fixtures.append({'dt': 'Custom Field', 'filters': [['fieldname', 'in', ['email_verified_at', 'phone_verified_at', 'email_verification_token', 'custom_refresh_token', 'custom_token_expiry']]]})
fixtures.append({'dt': 'Email Template', 'filters': [['name', 'in', ['Resend Verification']]]})
auth_hooks = globals().get('auth_hooks', [])
if 'rcore.auth.api.auth.auth.validate' not in auth_hooks: auth_hooks.append('rcore.auth.api.auth.auth.validate')

# --- Module: users ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('daily', [])
for _t in ['rcore.users.users.tasks.disable_expired_support_users', 'rcore.users.users.tasks.archive_inactive_vault_files']:
    if _t not in scheduler_events['daily']: scheduler_events['daily'].append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.user.delete_account'] = 'rcore.users.api.user.delete_account'
override_whitelisted_methods['rcore.api.user.delete_account'] = 'rcore.users.api.user.delete_account'
whitelisted_methods['rcore.api.user.forgot_password_confirm'] = 'rcore.users.api.user.forgot_password_confirm'
override_whitelisted_methods['rcore.api.user.forgot_password_confirm'] = 'rcore.users.api.user.forgot_password_confirm'
whitelisted_methods['rcore.api.user.login_with_google'] = 'rcore.users.api.user.login_with_google'
override_whitelisted_methods['rcore.api.user.login_with_google'] = 'rcore.users.api.user.login_with_google'
whitelisted_methods['rcore.api.user.search_user'] = 'rcore.users.api.user.search_user'
override_whitelisted_methods['rcore.api.user.search_user'] = 'rcore.users.api.user.search_user'
whitelisted_methods['rcore.api.user.send_wallet_balance'] = 'rcore.users.api.user.send_wallet_balance'
override_whitelisted_methods['rcore.api.user.send_wallet_balance'] = 'rcore.users.api.user.send_wallet_balance'
whitelisted_methods['rcore.api.user.register_user'] = 'rcore.users.api.user.register_user'
override_whitelisted_methods['rcore.api.user.register_user'] = 'rcore.users.api.user.register_user'
whitelisted_methods['rcore.api.user.update_password'] = 'rcore.users.api.user.update_password'
override_whitelisted_methods['rcore.api.user.update_password'] = 'rcore.users.api.user.update_password'
whitelisted_methods['rcore.api.user.update_profile_image'] = 'rcore.users.api.user.update_profile_image'
override_whitelisted_methods['rcore.api.user.update_profile_image'] = 'rcore.users.api.user.update_profile_image'
whitelisted_methods['rcore.api.user.add_user_address'] = 'rcore.users.api.user.add_user_address'
override_whitelisted_methods['rcore.api.user.add_user_address'] = 'rcore.users.api.user.add_user_address'
whitelisted_methods['rcore.api.user.check_phone'] = 'rcore.users.api.user.check_phone'
override_whitelisted_methods['rcore.api.user.check_phone'] = 'rcore.users.api.user.check_phone'
whitelisted_methods['rcore.api.user.create_invite'] = 'rcore.users.api.user.create_invite'
override_whitelisted_methods['rcore.api.user.create_invite'] = 'rcore.users.api.user.create_invite'
whitelisted_methods['rcore.api.user.create_order_refund'] = 'rcore.users.api.user.create_order_refund'
override_whitelisted_methods['rcore.api.user.create_order_refund'] = 'rcore.users.api.user.create_order_refund'
whitelisted_methods['rcore.api.user.create_request_model'] = 'rcore.users.api.user.create_request_model'
override_whitelisted_methods['rcore.api.user.create_request_model'] = 'rcore.users.api.user.create_request_model'
whitelisted_methods['rcore.api.user.create_ticket'] = 'rcore.users.api.user.create_ticket'
override_whitelisted_methods['rcore.api.user.create_ticket'] = 'rcore.users.api.user.create_ticket'
whitelisted_methods['rcore.api.user.delete_user_address'] = 'rcore.users.api.user.delete_user_address'
override_whitelisted_methods['rcore.api.user.delete_user_address'] = 'rcore.users.api.user.delete_user_address'
whitelisted_methods['rcore.api.user.export_orders'] = 'rcore.users.api.user.export_orders'
override_whitelisted_methods['rcore.api.user.export_orders'] = 'rcore.users.api.user.export_orders'
whitelisted_methods['rcore.api.user.forgot_password'] = 'rcore.users.api.user.forgot_password'
override_whitelisted_methods['rcore.api.user.forgot_password'] = 'rcore.users.api.user.forgot_password'
whitelisted_methods['rcore.api.user.get_profile'] = 'rcore.users.api.user.get_profile'
override_whitelisted_methods['rcore.api.user.get_profile'] = 'rcore.users.api.user.get_profile'
whitelisted_methods['rcore.api.user.get_user_address'] = 'rcore.users.api.user.get_user_address'
override_whitelisted_methods['rcore.api.user.get_user_address'] = 'rcore.users.api.user.get_user_address'
whitelisted_methods['rcore.api.user.get_user_addresses'] = 'rcore.users.api.user.get_user_addresses'
override_whitelisted_methods['rcore.api.user.get_user_addresses'] = 'rcore.users.api.user.get_user_addresses'
whitelisted_methods['rcore.api.user.get_referral_details'] = 'rcore.users.api.user.get_referral_details'
override_whitelisted_methods['rcore.api.user.get_referral_details'] = 'rcore.users.api.user.get_referral_details'
whitelisted_methods['rcore.api.user.set_active_address'] = 'rcore.users.api.user.set_active_address'
override_whitelisted_methods['rcore.api.user.set_active_address'] = 'rcore.users.api.user.set_active_address'
whitelisted_methods['rcore.api.user.get_user_invites'] = 'rcore.users.api.user.get_user_invites'
override_whitelisted_methods['rcore.api.user.get_user_invites'] = 'rcore.users.api.user.get_user_invites'
whitelisted_methods['rcore.api.user.get_user_membership'] = 'rcore.users.api.user.get_user_membership'
override_whitelisted_methods['rcore.api.user.get_user_membership'] = 'rcore.users.api.user.get_user_membership'
whitelisted_methods['rcore.api.user.get_user_membership_history'] = 'rcore.users.api.user.get_user_membership_history'
override_whitelisted_methods['rcore.api.user.get_user_membership_history'] = 'rcore.users.api.user.get_user_membership_history'
whitelisted_methods['rcore.api.user.get_user_notifications'] = 'rcore.users.api.user.get_user_notifications'
override_whitelisted_methods['rcore.api.user.get_user_notifications'] = 'rcore.users.api.user.get_user_notifications'
whitelisted_methods['rcore.api.user.get_user_order_refunds'] = 'rcore.users.api.user.get_user_order_refunds'
override_whitelisted_methods['rcore.api.user.get_user_order_refunds'] = 'rcore.users.api.user.get_user_order_refunds'
whitelisted_methods['rcore.api.user.get_user_parcel_order'] = 'rcore.users.api.user.get_user_parcel_order'
override_whitelisted_methods['rcore.api.user.get_user_parcel_order'] = 'rcore.users.api.user.get_user_parcel_order'
whitelisted_methods['rcore.api.user.get_user_parcel_orders'] = 'rcore.users.api.user.get_user_parcel_orders'
override_whitelisted_methods['rcore.api.user.get_user_parcel_orders'] = 'rcore.users.api.user.get_user_parcel_orders'
whitelisted_methods['rcore.api.user.get_user_profile'] = 'rcore.users.api.user.get_user_profile'
override_whitelisted_methods['rcore.api.user.get_user_profile'] = 'rcore.users.api.user.get_user_profile'
whitelisted_methods['rcore.api.user.get_user_request_models'] = 'rcore.users.api.user.get_user_request_models'
override_whitelisted_methods['rcore.api.user.get_user_request_models'] = 'rcore.users.api.user.get_user_request_models'
whitelisted_methods['rcore.api.user.get_user_shop'] = 'rcore.users.api.user.get_user_shop'
override_whitelisted_methods['rcore.api.user.get_user_shop'] = 'rcore.users.api.user.get_user_shop'
whitelisted_methods['rcore.api.user.get_user_ticket'] = 'rcore.users.api.user.get_user_ticket'
override_whitelisted_methods['rcore.api.user.get_user_ticket'] = 'rcore.users.api.user.get_user_ticket'
whitelisted_methods['rcore.api.user.get_user_tickets'] = 'rcore.users.api.user.get_user_tickets'
override_whitelisted_methods['rcore.api.user.get_user_tickets'] = 'rcore.users.api.user.get_user_tickets'
whitelisted_methods['rcore.api.user.get_user_transactions'] = 'rcore.users.api.user.get_user_transactions'
override_whitelisted_methods['rcore.api.user.get_user_transactions'] = 'rcore.users.api.user.get_user_transactions'
whitelisted_methods['rcore.api.user.get_user_wallet'] = 'rcore.users.api.user.get_user_wallet'
override_whitelisted_methods['rcore.api.user.get_user_wallet'] = 'rcore.users.api.user.get_user_wallet'
whitelisted_methods['rcore.api.user.get_weak_concepts'] = 'rcore.users.api.user.get_weak_concepts'
override_whitelisted_methods['rcore.api.user.get_weak_concepts'] = 'rcore.users.api.user.get_weak_concepts'
whitelisted_methods['rcore.api.user.get_wallet_history'] = 'rcore.users.api.user.get_wallet_history'
override_whitelisted_methods['rcore.api.user.get_wallet_history'] = 'rcore.users.api.user.get_wallet_history'
whitelisted_methods['rcore.api.user.login'] = 'rcore.users.api.user.login'
override_whitelisted_methods['rcore.api.user.login'] = 'rcore.users.api.user.login'
whitelisted_methods['rcore.api.user.logout'] = 'rcore.users.api.user.logout'
override_whitelisted_methods['rcore.api.user.logout'] = 'rcore.users.api.user.logout'
whitelisted_methods['rcore.api.user.register_device_token'] = 'rcore.users.api.user.register_device_token'
override_whitelisted_methods['rcore.api.user.register_device_token'] = 'rcore.users.api.user.register_device_token'
whitelisted_methods['rcore.api.user.resend_verification_email'] = 'rcore.users.api.user.resend_verification_email'
override_whitelisted_methods['rcore.api.user.resend_verification_email'] = 'rcore.users.api.user.resend_verification_email'
whitelisted_methods['rcore.api.resend_verification_email'] = 'rcore.users.api.user.resend_verification_email'
override_whitelisted_methods['rcore.api.resend_verification_email'] = 'rcore.users.api.user.resend_verification_email'
whitelisted_methods['rcore.api.user.reply_to_ticket'] = 'rcore.users.api.user.reply_to_ticket'
override_whitelisted_methods['rcore.api.user.reply_to_ticket'] = 'rcore.users.api.user.reply_to_ticket'
whitelisted_methods['rcore.api.user.send_phone_verification_code'] = 'rcore.users.api.user.send_phone_verification_code'
override_whitelisted_methods['rcore.api.user.send_phone_verification_code'] = 'rcore.users.api.user.send_phone_verification_code'
whitelisted_methods['rcore.api.user.update_invite_status'] = 'rcore.users.api.user.update_invite_status'
override_whitelisted_methods['rcore.api.user.update_invite_status'] = 'rcore.users.api.user.update_invite_status'
whitelisted_methods['rcore.api.user.update_profile'] = 'rcore.users.api.user.update_profile'
override_whitelisted_methods['rcore.api.user.update_profile'] = 'rcore.users.api.user.update_profile'
whitelisted_methods['rcore.api.user.update_seller_shop'] = 'rcore.users.api.user.update_seller_shop'
override_whitelisted_methods['rcore.api.user.update_seller_shop'] = 'rcore.users.api.user.update_seller_shop'
whitelisted_methods['rcore.api.user.update_user_address'] = 'rcore.users.api.user.update_user_address'
override_whitelisted_methods['rcore.api.user.update_user_address'] = 'rcore.users.api.user.update_user_address'
whitelisted_methods['rcore.api.user.update_user_profile'] = 'rcore.users.api.user.update_user_profile'
override_whitelisted_methods['rcore.api.user.update_user_profile'] = 'rcore.users.api.user.update_user_profile'
whitelisted_methods['rcore.api.user.update_user_shop'] = 'rcore.users.api.user.update_user_shop'
override_whitelisted_methods['rcore.api.user.update_user_shop'] = 'rcore.users.api.user.update_user_shop'
whitelisted_methods['rcore.api.user.verify_phone_code'] = 'rcore.users.api.user.verify_phone_code'
override_whitelisted_methods['rcore.api.user.verify_phone_code'] = 'rcore.users.api.user.verify_phone_code'
whitelisted_methods['rcore.api.user.verify_email_code'] = 'rcore.users.api.user.verify_email_code'
override_whitelisted_methods['rcore.api.user.verify_email_code'] = 'rcore.users.api.user.verify_email_code'
whitelisted_methods['rcore.tenant.api.create_temporary_support_user'] = 'rcore.users.users.create_temporary_support_user.create_temporary_support_user'
override_whitelisted_methods['rcore.tenant.api.create_temporary_support_user'] = 'rcore.users.users.create_temporary_support_user.create_temporary_support_user'
whitelisted_methods['rcore.tenant.api.disable_temporary_support_user'] = 'rcore.users.users.disable_temporary_support_user.disable_temporary_support_user'
override_whitelisted_methods['rcore.tenant.api.disable_temporary_support_user'] = 'rcore.users.users.disable_temporary_support_user.disable_temporary_support_user'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'User Address']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Google User']]})
fixtures.append({'dt': 'Role', 'filters': [['name', 'in', ['Seller', 'Company Creator']]]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Family Member']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Guardian Preference']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Insurance Policy']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Nominee']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Partner Member']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Partner Organization']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Employee Warning']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Company Policy']]})

# --- Module: subscriptions ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('daily', [])
for _t in ['rcore.subscriptions.subscriptions.tasks.reset_monthly_token_usage', 'rcore.subscriptions.subscriptions.tasks.update_storage_usage']:
    if _t not in scheduler_events['daily']: scheduler_events['daily'].append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.subscription.assign_subscription_to_shop'] = 'rcore.subscriptions.api.subscription.subscription.assign_subscription_to_shop'
override_whitelisted_methods['rcore.api.subscription.assign_subscription_to_shop'] = 'rcore.subscriptions.api.subscription.subscription.assign_subscription_to_shop'
whitelisted_methods['rcore.api.subscription.cancel_shop_subscription'] = 'rcore.subscriptions.api.subscription.subscription.cancel_shop_subscription'
override_whitelisted_methods['rcore.api.subscription.cancel_shop_subscription'] = 'rcore.subscriptions.api.subscription.subscription.cancel_shop_subscription'
whitelisted_methods['rcore.api.subscription.create_subscription'] = 'rcore.subscriptions.api.subscription.subscription.create_subscription'
override_whitelisted_methods['rcore.api.subscription.create_subscription'] = 'rcore.subscriptions.api.subscription.subscription.create_subscription'
whitelisted_methods['rcore.api.subscription.delete_subscription'] = 'rcore.subscriptions.api.subscription.subscription.delete_subscription'
override_whitelisted_methods['rcore.api.subscription.delete_subscription'] = 'rcore.subscriptions.api.subscription.subscription.delete_subscription'
whitelisted_methods['rcore.api.subscription.get_my_shop_subscription'] = 'rcore.subscriptions.api.subscription.subscription.get_my_shop_subscription'
override_whitelisted_methods['rcore.api.subscription.get_my_shop_subscription'] = 'rcore.subscriptions.api.subscription.subscription.get_my_shop_subscription'
whitelisted_methods['rcore.api.subscription.get_shop_subscriptions'] = 'rcore.subscriptions.api.subscription.subscription.get_shop_subscriptions'
override_whitelisted_methods['rcore.api.subscription.get_shop_subscriptions'] = 'rcore.subscriptions.api.subscription.subscription.get_shop_subscriptions'
whitelisted_methods['rcore.api.subscription.get_subscription'] = 'rcore.subscriptions.api.subscription.subscription.get_subscription'
override_whitelisted_methods['rcore.api.subscription.get_subscription'] = 'rcore.subscriptions.api.subscription.subscription.get_subscription'
whitelisted_methods['rcore.api.subscription.list_subscriptions'] = 'rcore.subscriptions.api.subscription.subscription.list_subscriptions'
override_whitelisted_methods['rcore.api.subscription.list_subscriptions'] = 'rcore.subscriptions.api.subscription.subscription.list_subscriptions'
whitelisted_methods['rcore.api.subscription.subscribe_my_shop'] = 'rcore.subscriptions.api.subscription.subscription.subscribe_my_shop'
override_whitelisted_methods['rcore.api.subscription.subscribe_my_shop'] = 'rcore.subscriptions.api.subscription.subscription.subscribe_my_shop'
whitelisted_methods['rcore.api.subscription.update_shop_subscription'] = 'rcore.subscriptions.api.subscription.subscription.update_shop_subscription'
override_whitelisted_methods['rcore.api.subscription.update_shop_subscription'] = 'rcore.subscriptions.api.subscription.subscription.update_shop_subscription'
whitelisted_methods['rcore.api.subscription.update_subscription'] = 'rcore.subscriptions.api.subscription.subscription.update_subscription'
override_whitelisted_methods['rcore.api.subscription.update_subscription'] = 'rcore.subscriptions.api.subscription.subscription.update_subscription'
whitelisted_methods['rcore.tenant.api.get_subscription_details'] = 'rcore.subscriptions.subscriptions.get_subscription_details.get_subscription_details'
override_whitelisted_methods['rcore.tenant.api.get_subscription_details'] = 'rcore.subscriptions.subscriptions.get_subscription_details.get_subscription_details'
whitelisted_methods['rcore.tenant.api.record_token_usage'] = 'rcore.subscriptions.subscriptions.record_token_usage.record_token_usage'
override_whitelisted_methods['rcore.tenant.api.record_token_usage'] = 'rcore.subscriptions.subscriptions.record_token_usage.record_token_usage'
whitelisted_methods['rcore.tenant.api.get_token_usage'] = 'rcore.subscriptions.subscriptions.get_token_usage.get_token_usage'
override_whitelisted_methods['rcore.tenant.api.get_token_usage'] = 'rcore.subscriptions.subscriptions.get_token_usage.get_token_usage'
whitelisted_methods['rcore.tenant.api.sync_usage_to_control'] = 'rcore.subscriptions.subscriptions.sync_usage_to_control.sync_usage_to_control'
override_whitelisted_methods['rcore.tenant.api.sync_usage_to_control'] = 'rcore.subscriptions.subscriptions.sync_usage_to_control.sync_usage_to_control'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Subscription']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Membership']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop Subscription']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'User Membership']]})
fixtures.append({'dt': 'Custom Field', 'filters': [['fieldname', 'in', ['company_license', 'stripe_customer_id']]]})
fixtures.append({'dt': 'Email Template', 'filters': [['name', 'in', ['Trial Ending Soon']]]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Storage Tracker']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Token Usage Tracker']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Tenant Email Settings']]})

# --- Module: agent ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('hourly', [])
for _t in ['rcore.agent.brain.frontend_error_alerts.send_frontend_error_digest']:
    if _t not in scheduler_events['hourly']: scheduler_events['hourly'].append(_t)
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('daily', [])
for _t in ['rcore.agent.brain.tasks.manage_daily_tenders', 'rcore.agent.brain.tasks.manage_daily_funding', 'rcore.agent.brain.tasks.pick_proactive_question', 'rcore.agent.brain.tasks.archive_low_score_engrams']:
    if _t not in scheduler_events['daily']: scheduler_events['daily'].append(_t)
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('cron', {})
_cron_jobs = scheduler_events['cron'].setdefault('*/15 * * * *', [])
for _t in ['rcore.agent.roadmap.tasks.dispatch_build_queue_to_github']:
    if _t not in _cron_jobs: _cron_jobs.append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.ask_assistant'] = 'rcore.agent.brain.ask_assistant.ask_assistant'
override_whitelisted_methods['rcore.api.ask_assistant'] = 'rcore.agent.brain.ask_assistant.ask_assistant'
whitelisted_methods['rcore.api.query'] = 'rcore.agent.brain.query.query'
override_whitelisted_methods['rcore.api.query'] = 'rcore.agent.brain.query.query'
whitelisted_methods['rcore.api.search'] = 'rcore.agent.brain.search.search'
override_whitelisted_methods['rcore.api.search'] = 'rcore.agent.brain.search.search'
whitelisted_methods['rcore.api.record_event'] = 'rcore.agent.brain.record_event.record_event'
override_whitelisted_methods['rcore.api.record_event'] = 'rcore.agent.brain.record_event.record_event'
whitelisted_methods['rcore.api.record_chat_summary'] = 'rcore.agent.brain.record_chat_summary.record_chat_summary'
override_whitelisted_methods['rcore.api.record_chat_summary'] = 'rcore.agent.brain.record_chat_summary.record_chat_summary'
whitelisted_methods['rcore.api.get_event_interval'] = 'rcore.agent.brain.get_event_interval.get_event_interval'
override_whitelisted_methods['rcore.api.get_event_interval'] = 'rcore.agent.brain.get_event_interval.get_event_interval'
whitelisted_methods['rcore.api.accept_stimulus'] = 'rcore.agent.brain.accept_stimulus.accept_stimulus'
override_whitelisted_methods['rcore.api.accept_stimulus'] = 'rcore.agent.brain.accept_stimulus.accept_stimulus'
whitelisted_methods['rcore.api.reject_stimulus'] = 'rcore.agent.brain.reject_stimulus.reject_stimulus'
override_whitelisted_methods['rcore.api.reject_stimulus'] = 'rcore.agent.brain.reject_stimulus.reject_stimulus'
whitelisted_methods['rcore.api.accept_neurotrophin'] = 'rcore.agent.brain.accept_neurotrophin.accept_neurotrophin'
override_whitelisted_methods['rcore.api.accept_neurotrophin'] = 'rcore.agent.brain.accept_neurotrophin.accept_neurotrophin'
whitelisted_methods['rcore.api.reject_neurotrophin'] = 'rcore.agent.brain.reject_neurotrophin.reject_neurotrophin'
override_whitelisted_methods['rcore.api.reject_neurotrophin'] = 'rcore.agent.brain.reject_neurotrophin.reject_neurotrophin'
whitelisted_methods['rcore.api.dispatch_ai_task'] = 'rcore.agent.brain.dispatch_ai_task.dispatch_ai_task'
override_whitelisted_methods['rcore.api.dispatch_ai_task'] = 'rcore.agent.brain.dispatch_ai_task.dispatch_ai_task'
whitelisted_methods['rcore.api.get_ai_result'] = 'rcore.agent.brain.get_ai_result.get_ai_result'
override_whitelisted_methods['rcore.api.get_ai_result'] = 'rcore.agent.brain.get_ai_result.get_ai_result'
whitelisted_methods['rcore.api.generate_release_notes'] = 'rcore.agent.brain.generate_release_notes.generate_release_notes'
override_whitelisted_methods['rcore.api.generate_release_notes'] = 'rcore.agent.brain.generate_release_notes.generate_release_notes'
whitelisted_methods['rcore.api.delete_jules_session'] = 'rcore.agent.brain.delete_jules_session.delete_jules_session'
override_whitelisted_methods['rcore.api.delete_jules_session'] = 'rcore.agent.brain.delete_jules_session.delete_jules_session'
whitelisted_methods['rcore.api.generate_summary_and_update_engram'] = 'rcore.agent.brain.generate_summary_and_update_engram.generate_summary_and_update_engram'
override_whitelisted_methods['rcore.api.generate_summary_and_update_engram'] = 'rcore.agent.brain.generate_summary_and_update_engram.generate_summary_and_update_engram'
whitelisted_methods['rcore.api.get_jules_activities'] = 'rcore.agent.brain.get_jules_activities.get_jules_activities'
override_whitelisted_methods['rcore.api.get_jules_activities'] = 'rcore.agent.brain.get_jules_activities.get_jules_activities'
whitelisted_methods['rcore.api.get_jules_sessions'] = 'rcore.agent.brain.get_jules_sessions.get_jules_sessions'
override_whitelisted_methods['rcore.api.get_jules_sessions'] = 'rcore.agent.brain.get_jules_sessions.get_jules_sessions'
whitelisted_methods['rcore.api.get_jules_sources'] = 'rcore.agent.brain.get_jules_sources.get_jules_sources'
override_whitelisted_methods['rcore.api.get_jules_sources'] = 'rcore.agent.brain.get_jules_sources.get_jules_sources'
whitelisted_methods['rcore.api.get_jules_status'] = 'rcore.agent.brain.get_jules_status.get_jules_status'
override_whitelisted_methods['rcore.api.get_jules_status'] = 'rcore.agent.brain.get_jules_status.get_jules_status'
whitelisted_methods['rcore.api.semantic_search'] = 'rcore.agent.brain.semantic_search.semantic_search'
override_whitelisted_methods['rcore.api.semantic_search'] = 'rcore.agent.brain.semantic_search.semantic_search'
whitelisted_methods['rcore.api.send_jules_message'] = 'rcore.agent.brain.send_jules_message.send_jules_message'
override_whitelisted_methods['rcore.api.send_jules_message'] = 'rcore.agent.brain.send_jules_message.send_jules_message'
whitelisted_methods['rcore.api.start_jules_session'] = 'rcore.agent.brain.start_jules_session.start_jules_session'
override_whitelisted_methods['rcore.api.start_jules_session'] = 'rcore.agent.brain.start_jules_session.start_jules_session'
whitelisted_methods['rcore.api.vote_on_plan'] = 'rcore.agent.brain.vote_on_plan.vote_on_plan'
override_whitelisted_methods['rcore.api.vote_on_plan'] = 'rcore.agent.brain.vote_on_plan.vote_on_plan'
whitelisted_methods['rcore.api.plan_builder.chat_with_rok'] = 'rcore.agent.plan_builder.chat_with_rok.chat_with_rok'
override_whitelisted_methods['rcore.api.plan_builder.chat_with_rok'] = 'rcore.agent.plan_builder.chat_with_rok.chat_with_rok'
whitelisted_methods['rcore.api.plan_builder.commit_onboarding_answers'] = 'rcore.agent.plan_builder.commit_onboarding_answers.commit_onboarding_answers'
override_whitelisted_methods['rcore.api.plan_builder.commit_onboarding_answers'] = 'rcore.agent.plan_builder.commit_onboarding_answers.commit_onboarding_answers'
whitelisted_methods['rcore.api.plan_builder.commit_plan'] = 'rcore.agent.plan_builder.commit_plan.commit_plan'
override_whitelisted_methods['rcore.api.plan_builder.commit_plan'] = 'rcore.agent.plan_builder.commit_plan.commit_plan'
whitelisted_methods['rcore.api.plan_builder.ensure_startup_os_core'] = 'rcore.agent.plan_builder.ensure_startup_os_core.ensure_startup_os_core'
override_whitelisted_methods['rcore.api.plan_builder.ensure_startup_os_core'] = 'rcore.agent.plan_builder.ensure_startup_os_core.ensure_startup_os_core'
whitelisted_methods['rcore.api.plan_builder.generate_alive_cv_pdf'] = 'rcore.agent.plan_builder.generate_alive_cv_pdf.generate_alive_cv_pdf'
override_whitelisted_methods['rcore.api.plan_builder.generate_alive_cv_pdf'] = 'rcore.agent.plan_builder.generate_alive_cv_pdf.generate_alive_cv_pdf'
whitelisted_methods['rcore.api.plan_builder.generate_strategic_alignment_report'] = 'rcore.agent.plan_builder.generate_strategic_alignment_report.generate_strategic_alignment_report'
override_whitelisted_methods['rcore.api.plan_builder.generate_strategic_alignment_report'] = 'rcore.agent.plan_builder.generate_strategic_alignment_report.generate_strategic_alignment_report'
whitelisted_methods['rcore.api.plan_builder.get_available_models'] = 'rcore.agent.plan_builder.get_available_models.get_available_models'
override_whitelisted_methods['rcore.api.plan_builder.get_available_models'] = 'rcore.agent.plan_builder.get_available_models.get_available_models'
whitelisted_methods['rcore.api.plan_builder.perform_bootstrap_secrets_handshake'] = 'rcore.agent.plan_builder.perform_bootstrap_secrets_handshake.perform_bootstrap_secrets_handshake'
override_whitelisted_methods['rcore.api.plan_builder.perform_bootstrap_secrets_handshake'] = 'rcore.agent.plan_builder.perform_bootstrap_secrets_handshake.perform_bootstrap_secrets_handshake'
whitelisted_methods['rcore.api.plan_builder.summarize_chat_session'] = 'rcore.agent.plan_builder.summarize_chat_session.summarize_chat_session'
override_whitelisted_methods['rcore.api.plan_builder.summarize_chat_session'] = 'rcore.agent.plan_builder.summarize_chat_session.summarize_chat_session'
whitelisted_methods['rcore.api.roadmap.update_task_status_from_pr'] = 'rcore.agent.roadmap.api.update_task_status_from_pr'
override_whitelisted_methods['rcore.api.roadmap.update_task_status_from_pr'] = 'rcore.agent.roadmap.api.update_task_status_from_pr'
whitelisted_methods['rcore.api.update_tenant_ecosystem'] = 'rcore.agent.brain.update_manager.update_tenant_ecosystem'
override_whitelisted_methods['rcore.api.update_tenant_ecosystem'] = 'rcore.agent.brain.update_manager.update_tenant_ecosystem'
doc_events = globals().get('doc_events', {})
doc_events.setdefault('Engram', {})
_ev = doc_events['Engram'].get('before_insert') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.agent.brain.tasks.tag_engram_pillars']:
    if _h not in _ev: _ev.append(_h)
doc_events['Engram']['before_insert'] = _ev
_ev = doc_events['Engram'].get('validate') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.agent.brain.tasks.tag_engram_pillars']:
    if _h not in _ev: _ev.append(_h)
doc_events['Engram']['validate'] = _ev
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Engram']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Engram Permission']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Question Bank']]})
after_install = globals().get('after_install', [])
if 'rcore.agent.brain.install.fetch_agent_scripts' not in after_install: after_install.append('rcore.agent.brain.install.fetch_agent_scripts')

# --- Module: polaris ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.lending.check_loan_eligibility'] = 'rcore.polaris.rlending.api.lending_mocks.check_loan_eligibility'
override_whitelisted_methods['rcore.api.lending.check_loan_eligibility'] = 'rcore.polaris.rlending.api.lending_mocks.check_loan_eligibility'
whitelisted_methods['rcore.api.lending.check_loan_history_eligibility'] = 'rcore.polaris.rlending.api.lending_mocks.check_loan_history_eligibility'
override_whitelisted_methods['rcore.api.lending.check_loan_history_eligibility'] = 'rcore.polaris.rlending.api.lending_mocks.check_loan_history_eligibility'
whitelisted_methods['rcore.api.lending.mark_application_as_rejected'] = 'rcore.polaris.rlending.api.lending_mocks.mark_application_as_rejected'
override_whitelisted_methods['rcore.api.lending.mark_application_as_rejected'] = 'rcore.polaris.rlending.api.lending_mocks.mark_application_as_rejected'
whitelisted_methods['rcore.api.lending.check_financial_eligibility'] = 'rcore.polaris.rlending.api.lending_mocks.check_financial_eligibility'
override_whitelisted_methods['rcore.api.lending.check_financial_eligibility'] = 'rcore.polaris.rlending.api.lending_mocks.check_financial_eligibility'
whitelisted_methods['rcore.api.lending.save_incomplete_loan_application'] = 'rcore.polaris.rlending.api.lending_mocks.save_incomplete_loan_application'
override_whitelisted_methods['rcore.api.lending.save_incomplete_loan_application'] = 'rcore.polaris.rlending.api.lending_mocks.save_incomplete_loan_application'
whitelisted_methods['rcore.api.lending.fetch_saved_application'] = 'rcore.polaris.rlending.api.lending_mocks.fetch_saved_application'
override_whitelisted_methods['rcore.api.lending.fetch_saved_application'] = 'rcore.polaris.rlending.api.lending_mocks.fetch_saved_application'
whitelisted_methods['rcore.api.lending.fetch_saved_applications'] = 'rcore.polaris.rlending.api.lending_mocks.fetch_saved_applications'
override_whitelisted_methods['rcore.api.lending.fetch_saved_applications'] = 'rcore.polaris.rlending.api.lending_mocks.fetch_saved_applications'
whitelisted_methods['rcore.api.lending.create_loan_application'] = 'rcore.polaris.rlending.api.lending_mocks.create_loan_application'
override_whitelisted_methods['rcore.api.lending.create_loan_application'] = 'rcore.polaris.rlending.api.lending_mocks.create_loan_application'
whitelisted_methods['rcore.api.lending.get_my_loan_applications'] = 'rcore.polaris.rlending.api.lending_mocks.get_my_loan_applications'
override_whitelisted_methods['rcore.api.lending.get_my_loan_applications'] = 'rcore.polaris.rlending.api.lending_mocks.get_my_loan_applications'
whitelisted_methods['rcore.api.lending.disburse_loan'] = 'rcore.polaris.rlending.api.loan.disburse_loan'
override_whitelisted_methods['rcore.api.lending.disburse_loan'] = 'rcore.polaris.rlending.api.loan.disburse_loan'
whitelisted_methods['rcore.api.lending.get_credit_score'] = 'rcore.polaris.rlending.api.decision.get_credit_score'
override_whitelisted_methods['rcore.api.lending.get_credit_score'] = 'rcore.polaris.rlending.api.decision.get_credit_score'
whitelisted_methods['rcore.api.lending.get_loan_product_list'] = 'rcore.polaris.rlending.api.product.get_loan_product_list'
override_whitelisted_methods['rcore.api.lending.get_loan_product_list'] = 'rcore.polaris.rlending.api.product.get_loan_product_list'
whitelisted_methods['rcore.api.lending.run_interest_accrual'] = 'rcore.polaris.doctype.process_loan_interest_accrual.process_loan_interest_accrual.process_loan_interest_accrual_for_loans'
override_whitelisted_methods['rcore.api.lending.run_interest_accrual'] = 'rcore.polaris.doctype.process_loan_interest_accrual.process_loan_interest_accrual.process_loan_interest_accrual_for_loans'
whitelisted_methods['rcore.api.lending.run_security_shortfall_check'] = 'rcore.polaris.doctype.process_loan_security_shortfall.process_loan_security_shortfall.create_process_loan_security_shortfall'
override_whitelisted_methods['rcore.api.lending.run_security_shortfall_check'] = 'rcore.polaris.doctype.process_loan_security_shortfall.process_loan_security_shortfall.create_process_loan_security_shortfall'
whitelisted_methods['rcore.api.lending.run_loan_classification'] = 'rcore.polaris.doctype.process_loan_classification.process_loan_classification.create_process_loan_classification'
override_whitelisted_methods['rcore.api.lending.run_loan_classification'] = 'rcore.polaris.doctype.process_loan_classification.process_loan_classification.create_process_loan_classification'
whitelisted_methods['rcore.api.lending.release_security'] = 'rcore.polaris.rlending.asset_realisation.release_security'
override_whitelisted_methods['rcore.api.lending.release_security'] = 'rcore.polaris.rlending.asset_realisation.release_security'
doc_events = globals().get('doc_events', {})
doc_events.setdefault('Loan Disbursement', {})
_ev = doc_events['Loan Disbursement'].get('on_submit') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.polaris.rlending.wallet_integration.credit_wallet_on_disbursement']:
    if _h not in _ev: _ev.append(_h)
doc_events['Loan Disbursement']['on_submit'] = _ev
doc_events.setdefault('Loan Repayment', {})
_ev = doc_events['Loan Repayment'].get('on_submit') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.polaris.rlending.wallet_integration.debit_wallet_on_repayment']:
    if _h not in _ev: _ev.append(_h)
doc_events['Loan Repayment']['on_submit'] = _ev

# --- Module: telemetry ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('daily', [])
for _t in ['rcore.telemetry.telemetry.sync_visitors_to_control.sync_visitors_to_control']:
    if _t not in scheduler_events['daily']: scheduler_events['daily'].append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.tenant.api.report_client_error'] = 'rcore.telemetry.telemetry.forward_error_to_control.forward_error_to_control'
override_whitelisted_methods['rcore.tenant.api.report_client_error'] = 'rcore.telemetry.telemetry.forward_error_to_control.forward_error_to_control'
whitelisted_methods['rcore.tenant.api.log_frontend_error'] = 'rcore.telemetry.telemetry.log_frontend_error.log_frontend_error'
override_whitelisted_methods['rcore.tenant.api.log_frontend_error'] = 'rcore.telemetry.telemetry.log_frontend_error.log_frontend_error'
doc_events = globals().get('doc_events', {})
doc_events.setdefault('API Error Log', {})
_ev = doc_events['API Error Log'].get('after_insert') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.telemetry.telemetry.forward_error_to_control.forward_error_to_control']:
    if _h not in _ev: _ev.append(_h)
doc_events['API Error Log']['after_insert'] = _ev
doc_events.setdefault('*', {})
_ev = doc_events['*'].get('before_insert') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.telemetry.telemetry.utils.inject_trace_context']:
    if _h not in _ev: _ev.append(_h)
doc_events['*']['before_insert'] = _ev
_ev = doc_events['*'].get('validate') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.telemetry.telemetry.utils.inject_trace_context']:
    if _h not in _ev: _ev.append(_h)
doc_events['*']['validate'] = _ev
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'API Error Log']]})

# --- Module: productivity ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('daily', [])
for _t in ['rcore.productivity.productivity.tasks.send_weekly_goal_reminders', 'rcore.productivity.productivity.tasks.send_friday_wins_reminders']:
    if _t not in scheduler_events['daily']: scheduler_events['daily'].append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.tenant.api.get_visions'] = 'rcore.productivity.productivity.get_visions.get_visions'
override_whitelisted_methods['rcore.tenant.api.get_visions'] = 'rcore.productivity.productivity.get_visions.get_visions'
whitelisted_methods['rcore.tenant.api.get_pillars'] = 'rcore.productivity.productivity.get_pillars.get_pillars'
override_whitelisted_methods['rcore.tenant.api.get_pillars'] = 'rcore.productivity.productivity.get_pillars.get_pillars'
whitelisted_methods['rcore.tenant.api.get_strategic_objectives'] = 'rcore.productivity.productivity.get_strategic_objectives.get_strategic_objectives'
override_whitelisted_methods['rcore.tenant.api.get_strategic_objectives'] = 'rcore.productivity.productivity.get_strategic_objectives.get_strategic_objectives'
whitelisted_methods['rcore.tenant.api.get_kpis'] = 'rcore.productivity.productivity.get_kpis.get_kpis'
override_whitelisted_methods['rcore.tenant.api.get_kpis'] = 'rcore.productivity.productivity.get_kpis.get_kpis'
whitelisted_methods['rcore.tenant.api.get_plan_on_a_page'] = 'rcore.productivity.productivity.get_plan_on_a_page.get_plan_on_a_page'
override_whitelisted_methods['rcore.tenant.api.get_plan_on_a_page'] = 'rcore.productivity.productivity.get_plan_on_a_page.get_plan_on_a_page'
whitelisted_methods['rcore.tenant.api.get_personal_mastery_goals'] = 'rcore.productivity.productivity.get_personal_mastery_goals.get_personal_mastery_goals'
override_whitelisted_methods['rcore.tenant.api.get_personal_mastery_goals'] = 'rcore.productivity.productivity.get_personal_mastery_goals.get_personal_mastery_goals'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Vision']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Pillar']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'KPI']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Plan on a Page']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Personal Mastery Goal']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Strategic Objective']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Career Milestone']]})

# --- Module: weather ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.tenant.api.get_weather'] = 'rcore.weather.weather.get_weather.get_weather'
override_whitelisted_methods['rcore.tenant.api.get_weather'] = 'rcore.weather.weather.get_weather.get_weather'
whitelisted_methods['rcore.tenant.api.set_weather_alias'] = 'rcore.weather.weather.set_weather_alias.set_weather_alias'
override_whitelisted_methods['rcore.tenant.api.set_weather_alias'] = 'rcore.weather.weather.set_weather_alias.set_weather_alias'

# --- Module: lms ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('cron', {})
_cron_jobs = scheduler_events['cron'].setdefault('0 18 * * 0', [])
for _t in ['rcore.rlms.rlms.tasks.send_partner_weekly_digests']:
    if _t not in _cron_jobs: _cron_jobs.append(_t)
_cron_jobs = scheduler_events['cron'].setdefault('0 3 * * 1', [])
for _t in ['rcore.rlms.rlms.tasks.close_last_league_week']:
    if _t not in _cron_jobs: _cron_jobs.append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.lms.list_courses'] = 'rcore.rlms.rlms.api.course.list_courses'
override_whitelisted_methods['rcore.api.lms.list_courses'] = 'rcore.rlms.rlms.api.course.list_courses'
whitelisted_methods['rcore.api.lms.get_course_content'] = 'rcore.rlms.rlms.api.course.get_course_content'
override_whitelisted_methods['rcore.api.lms.get_course_content'] = 'rcore.rlms.rlms.api.course.get_course_content'
whitelisted_methods['rcore.api.lms.get_lesson_session'] = 'rcore.rlms.rlms.api.course.get_lesson_session'
override_whitelisted_methods['rcore.api.lms.get_lesson_session'] = 'rcore.rlms.rlms.api.course.get_lesson_session'
whitelisted_methods['rcore.api.lms.allowed_subjects'] = 'rcore.rlms.rlms.api.course.allowed_subjects'
override_whitelisted_methods['rcore.api.lms.allowed_subjects'] = 'rcore.rlms.rlms.api.course.allowed_subjects'
whitelisted_methods['rcore.api.lms.enroll'] = 'rcore.rlms.rlms.api.course.enroll'
override_whitelisted_methods['rcore.api.lms.enroll'] = 'rcore.rlms.rlms.api.course.enroll'
whitelisted_methods['rcore.api.lms.get_my_enrollment'] = 'rcore.rlms.rlms.api.course.get_my_enrollment'
override_whitelisted_methods['rcore.api.lms.get_my_enrollment'] = 'rcore.rlms.rlms.api.course.get_my_enrollment'
whitelisted_methods['rcore.api.lms.save_progress'] = 'rcore.rlms.rlms.api.progress.save_progress'
override_whitelisted_methods['rcore.api.lms.save_progress'] = 'rcore.rlms.rlms.api.progress.save_progress'
whitelisted_methods['rcore.api.lms.record_video_watch'] = 'rcore.rlms.rlms.api.progress.record_video_watch'
override_whitelisted_methods['rcore.api.lms.record_video_watch'] = 'rcore.rlms.rlms.api.progress.record_video_watch'
whitelisted_methods['rcore.api.lms.record_quiz_result'] = 'rcore.rlms.rlms.api.progress.record_quiz_result'
override_whitelisted_methods['rcore.api.lms.record_quiz_result'] = 'rcore.rlms.rlms.api.progress.record_quiz_result'
whitelisted_methods['rcore.api.lms.partner_invite'] = 'rcore.rlms.rlms.api.partner.invite'
override_whitelisted_methods['rcore.api.lms.partner_invite'] = 'rcore.rlms.rlms.api.partner.invite'
whitelisted_methods['rcore.api.lms.partner_accept_invite'] = 'rcore.rlms.rlms.api.partner.accept_invite'
override_whitelisted_methods['rcore.api.lms.partner_accept_invite'] = 'rcore.rlms.rlms.api.partner.accept_invite'
whitelisted_methods['rcore.api.lms.partner_my_status'] = 'rcore.rlms.rlms.api.partner.my_status'
override_whitelisted_methods['rcore.api.lms.partner_my_status'] = 'rcore.rlms.rlms.api.partner.my_status'
whitelisted_methods['rcore.api.lms.partner_weekly_report'] = 'rcore.rlms.rlms.api.partner.weekly_report'
override_whitelisted_methods['rcore.api.lms.partner_weekly_report'] = 'rcore.rlms.rlms.api.partner.weekly_report'
whitelisted_methods['rcore.api.lms.partner_my_students'] = 'rcore.rlms.rlms.api.partner.my_students'
override_whitelisted_methods['rcore.api.lms.partner_my_students'] = 'rcore.rlms.rlms.api.partner.my_students'
whitelisted_methods['rcore.api.lms.partner_signup'] = 'rcore.rlms.rlms.api.partner.signup'
override_whitelisted_methods['rcore.api.lms.partner_signup'] = 'rcore.rlms.rlms.api.partner.signup'
whitelisted_methods['rcore.api.lms.partner_invite_student'] = 'rcore.rlms.rlms.api.partner.invite_student'
override_whitelisted_methods['rcore.api.lms.partner_invite_student'] = 'rcore.rlms.rlms.api.partner.invite_student'
whitelisted_methods['rcore.api.lms.partner_redeem_student_invite'] = 'rcore.rlms.rlms.api.partner.redeem_student_invite'
override_whitelisted_methods['rcore.api.lms.partner_redeem_student_invite'] = 'rcore.rlms.rlms.api.partner.redeem_student_invite'
whitelisted_methods['rcore.api.lms.partner_assume_billing'] = 'rcore.rlms.rlms.api.partner.assume_billing'
override_whitelisted_methods['rcore.api.lms.partner_assume_billing'] = 'rcore.rlms.rlms.api.partner.assume_billing'
whitelisted_methods['rcore.api.lms.partner_release_billing'] = 'rcore.rlms.rlms.api.partner.release_billing'
override_whitelisted_methods['rcore.api.lms.partner_release_billing'] = 'rcore.rlms.rlms.api.partner.release_billing'
whitelisted_methods['rcore.api.lms.record_attendance_event'] = 'rcore.rlms.rlms.api.partner.record_attendance_event'
override_whitelisted_methods['rcore.api.lms.record_attendance_event'] = 'rcore.rlms.rlms.api.partner.record_attendance_event'
whitelisted_methods['rcore.api.lms.partner_unlink_student'] = 'rcore.rlms.rlms.api.partner.unlink_student'
override_whitelisted_methods['rcore.api.lms.partner_unlink_student'] = 'rcore.rlms.rlms.api.partner.unlink_student'
whitelisted_methods['rcore.api.lms.partner_alerts'] = 'rcore.rlms.rlms.api.partner.alerts'
override_whitelisted_methods['rcore.api.lms.partner_alerts'] = 'rcore.rlms.rlms.api.partner.alerts'
whitelisted_methods['rcore.api.lms.partner_enable_email_digest'] = 'rcore.rlms.rlms.api.partner.enable_email_digest'
override_whitelisted_methods['rcore.api.lms.partner_enable_email_digest'] = 'rcore.rlms.rlms.api.partner.enable_email_digest'
whitelisted_methods['rcore.api.lms.partner_disable_email_digest'] = 'rcore.rlms.rlms.api.partner.disable_email_digest'
override_whitelisted_methods['rcore.api.lms.partner_disable_email_digest'] = 'rcore.rlms.rlms.api.partner.disable_email_digest'
whitelisted_methods['rcore.api.lms.student_my_grade'] = 'rcore.rlms.rlms.api.student.my_grade'
override_whitelisted_methods['rcore.api.lms.student_my_grade'] = 'rcore.rlms.rlms.api.student.my_grade'
whitelisted_methods['rcore.api.lms.student_set_grade'] = 'rcore.rlms.rlms.api.student.set_grade'
override_whitelisted_methods['rcore.api.lms.student_set_grade'] = 'rcore.rlms.rlms.api.student.set_grade'
whitelisted_methods['rcore.api.lms.server_time'] = 'rcore.rlms.rlms.api.system.server_time'
override_whitelisted_methods['rcore.api.lms.server_time'] = 'rcore.rlms.rlms.api.system.server_time'
whitelisted_methods['rcore.api.lms.student_my_entitlements'] = 'rcore.rlms.rlms.api.student.my_entitlements'
override_whitelisted_methods['rcore.api.lms.student_my_entitlements'] = 'rcore.rlms.rlms.api.student.my_entitlements'
whitelisted_methods['rcore.api.lms.record_subscription_period'] = 'rcore.rlms.rlms.api.student.record_subscription_period'
override_whitelisted_methods['rcore.api.lms.record_subscription_period'] = 'rcore.rlms.rlms.api.student.record_subscription_period'
whitelisted_methods['rcore.api.lms.plans'] = 'rcore.rlms.rlms.api.billing.plans'
override_whitelisted_methods['rcore.api.lms.plans'] = 'rcore.rlms.rlms.api.billing.plans'
whitelisted_methods['rcore.api.lms.sponsor_checkout'] = 'rcore.rlms.rlms.api.billing.sponsor_checkout'
override_whitelisted_methods['rcore.api.lms.sponsor_checkout'] = 'rcore.rlms.rlms.api.billing.sponsor_checkout'
whitelisted_methods['rcore.api.lms.student_checkout'] = 'rcore.rlms.rlms.api.billing.student_checkout'
override_whitelisted_methods['rcore.api.lms.student_checkout'] = 'rcore.rlms.rlms.api.billing.student_checkout'
whitelisted_methods['rcore.api.lms.my_billing_history'] = 'rcore.rlms.rlms.api.billing.my_billing_history'
override_whitelisted_methods['rcore.api.lms.my_billing_history'] = 'rcore.rlms.rlms.api.billing.my_billing_history'
whitelisted_methods['rcore.api.lms.student_my_maths_track'] = 'rcore.rlms.rlms.api.student.my_maths_track'
override_whitelisted_methods['rcore.api.lms.student_my_maths_track'] = 'rcore.rlms.rlms.api.student.my_maths_track'
whitelisted_methods['rcore.api.lms.student_set_maths_track'] = 'rcore.rlms.rlms.api.student.set_maths_track'
override_whitelisted_methods['rcore.api.lms.student_set_maths_track'] = 'rcore.rlms.rlms.api.student.set_maths_track'
whitelisted_methods['rcore.api.lms.student_my_school'] = 'rcore.rlms.rlms.api.student.my_school'
override_whitelisted_methods['rcore.api.lms.student_my_school'] = 'rcore.rlms.rlms.api.student.my_school'
whitelisted_methods['rcore.api.lms.student_set_school'] = 'rcore.rlms.rlms.api.student.set_school'
override_whitelisted_methods['rcore.api.lms.student_set_school'] = 'rcore.rlms.rlms.api.student.set_school'
whitelisted_methods['rcore.api.lms.student_known_schools'] = 'rcore.rlms.rlms.api.student.known_schools'
override_whitelisted_methods['rcore.api.lms.student_known_schools'] = 'rcore.rlms.rlms.api.student.known_schools'
whitelisted_methods['rcore.api.lms.student_last_year_baseline'] = 'rcore.rlms.rlms.api.student.last_year_baseline'
override_whitelisted_methods['rcore.api.lms.student_last_year_baseline'] = 'rcore.rlms.rlms.api.student.last_year_baseline'
whitelisted_methods['rcore.api.lms.skills_index'] = 'rcore.rlms.rlms.api.skills.skills_index'
override_whitelisted_methods['rcore.api.lms.skills_index'] = 'rcore.rlms.rlms.api.skills.skills_index'
whitelisted_methods['rcore.api.lms.publish_skills_index'] = 'rcore.rlms.rlms.api.skills.publish_skills_index'
override_whitelisted_methods['rcore.api.lms.publish_skills_index'] = 'rcore.rlms.rlms.api.skills.publish_skills_index'
whitelisted_methods['rcore.api.lms.tutors'] = 'rcore.rlms.rlms.api.tutors.tutors'
override_whitelisted_methods['rcore.api.lms.tutors'] = 'rcore.rlms.rlms.api.tutors.tutors'
whitelisted_methods['rcore.api.lms.publish_tutors'] = 'rcore.rlms.rlms.api.tutors.publish_tutors'
override_whitelisted_methods['rcore.api.lms.publish_tutors'] = 'rcore.rlms.rlms.api.tutors.publish_tutors'
whitelisted_methods['rcore.api.lms.knowledge_bites_index'] = 'rcore.rlms.rlms.api.knowledge_bites.knowledge_bites_index'
override_whitelisted_methods['rcore.api.lms.knowledge_bites_index'] = 'rcore.rlms.rlms.api.knowledge_bites.knowledge_bites_index'
whitelisted_methods['rcore.api.lms.publish_knowledge_bites_index'] = 'rcore.rlms.rlms.api.knowledge_bites.publish_knowledge_bites_index'
override_whitelisted_methods['rcore.api.lms.publish_knowledge_bites_index'] = 'rcore.rlms.rlms.api.knowledge_bites.publish_knowledge_bites_index'
whitelisted_methods['rcore.api.lms.admin_review_lesson'] = 'rcore.rlms.rlms.api.admin.review_lesson'
override_whitelisted_methods['rcore.api.lms.admin_review_lesson'] = 'rcore.rlms.rlms.api.admin.review_lesson'
whitelisted_methods['rcore.api.lms.admin_can_review_lessons'] = 'rcore.rlms.rlms.api.admin.can_review_lessons'
override_whitelisted_methods['rcore.api.lms.admin_can_review_lessons'] = 'rcore.rlms.rlms.api.admin.can_review_lessons'
whitelisted_methods['rcore.api.lms.submit_homework_question'] = 'rcore.rlms.rlms.api.homework.submit_homework_question'
override_whitelisted_methods['rcore.api.lms.submit_homework_question'] = 'rcore.rlms.rlms.api.homework.submit_homework_question'
whitelisted_methods['rcore.api.lms.list_homework_questions'] = 'rcore.rlms.rlms.api.homework.list_homework_questions'
override_whitelisted_methods['rcore.api.lms.list_homework_questions'] = 'rcore.rlms.rlms.api.homework.list_homework_questions'
whitelisted_methods['rcore.api.lms.get_homework_question'] = 'rcore.rlms.rlms.api.homework.get_homework_question'
override_whitelisted_methods['rcore.api.lms.get_homework_question'] = 'rcore.rlms.rlms.api.homework.get_homework_question'
whitelisted_methods['rcore.api.lms.answer_homework_mcq'] = 'rcore.rlms.rlms.api.homework.answer_homework_mcq'
override_whitelisted_methods['rcore.api.lms.answer_homework_mcq'] = 'rcore.rlms.rlms.api.homework.answer_homework_mcq'
whitelisted_methods['rcore.api.lms.homework_pending_requests'] = 'rcore.rlms.rlms.api.homework.homework_pending_requests'
override_whitelisted_methods['rcore.api.lms.homework_pending_requests'] = 'rcore.rlms.rlms.api.homework.homework_pending_requests'
whitelisted_methods['rcore.api.lms.draft_homework_mcq'] = 'rcore.rlms.rlms.api.homework.draft_homework_mcq'
override_whitelisted_methods['rcore.api.lms.draft_homework_mcq'] = 'rcore.rlms.rlms.api.homework.draft_homework_mcq'
whitelisted_methods['rcore.api.lms.publish_homework_mcq'] = 'rcore.rlms.rlms.api.homework.publish_homework_mcq'
override_whitelisted_methods['rcore.api.lms.publish_homework_mcq'] = 'rcore.rlms.rlms.api.homework.publish_homework_mcq'
whitelisted_methods['rcore.api.lms.decline_homework_question'] = 'rcore.rlms.rlms.api.homework.decline_homework_question'
override_whitelisted_methods['rcore.api.lms.decline_homework_question'] = 'rcore.rlms.rlms.api.homework.decline_homework_question'
whitelisted_methods['rcore.api.lms.sponsor_dashboard'] = 'rcore.rlms.rlms.api.sponsor.sponsor_dashboard'
override_whitelisted_methods['rcore.api.lms.sponsor_dashboard'] = 'rcore.rlms.rlms.api.sponsor.sponsor_dashboard'
whitelisted_methods['rcore.api.lms.sponsor_outcome_report'] = 'rcore.rlms.rlms.api.sponsor.sponsor_outcome_report'
override_whitelisted_methods['rcore.api.lms.sponsor_outcome_report'] = 'rcore.rlms.rlms.api.sponsor.sponsor_outcome_report'
whitelisted_methods['rcore.api.lms.my_streak'] = 'rcore.rlms.rlms.api.engagement.my_streak'
override_whitelisted_methods['rcore.api.lms.my_streak'] = 'rcore.rlms.rlms.api.engagement.my_streak'
whitelisted_methods['rcore.api.lms.my_league'] = 'rcore.rlms.rlms.api.engagement.my_league'
override_whitelisted_methods['rcore.api.lms.my_league'] = 'rcore.rlms.rlms.api.engagement.my_league'
whitelisted_methods['rcore.api.lms.league_standings'] = 'rcore.rlms.rlms.api.engagement.league_standings'
override_whitelisted_methods['rcore.api.lms.league_standings'] = 'rcore.rlms.rlms.api.engagement.league_standings'
whitelisted_methods['rcore.api.lms.close_league_week'] = 'rcore.rlms.rlms.api.engagement.close_league_week'
override_whitelisted_methods['rcore.api.lms.close_league_week'] = 'rcore.rlms.rlms.api.engagement.close_league_week'
whitelisted_methods['rcore.api.lms.partner_students_league'] = 'rcore.rlms.rlms.api.engagement.partner_students_league'
override_whitelisted_methods['rcore.api.lms.partner_students_league'] = 'rcore.rlms.rlms.api.engagement.partner_students_league'
whitelisted_methods['rcore.api.lms.board_coverage'] = 'rcore.rlms.rlms.api.board.coverage'
override_whitelisted_methods['rcore.api.lms.board_coverage'] = 'rcore.rlms.rlms.api.board.coverage'
whitelisted_methods['rcore.api.lms.my_readiness'] = 'rcore.rlms.rlms.api.readiness.my_readiness'
override_whitelisted_methods['rcore.api.lms.my_readiness'] = 'rcore.rlms.rlms.api.readiness.my_readiness'
whitelisted_methods['rcore.api.lms.readiness_create_share'] = 'rcore.rlms.rlms.api.readiness.create_share'
override_whitelisted_methods['rcore.api.lms.readiness_create_share'] = 'rcore.rlms.rlms.api.readiness.create_share'
whitelisted_methods['rcore.api.lms.readiness_verify'] = 'rcore.rlms.rlms.api.readiness.verify'
override_whitelisted_methods['rcore.api.lms.readiness_verify'] = 'rcore.rlms.rlms.api.readiness.verify'
whitelisted_methods['rcore.api.lms.readiness_card'] = 'rcore.rlms.rlms.api.readiness.card'
override_whitelisted_methods['rcore.api.lms.readiness_card'] = 'rcore.rlms.rlms.api.readiness.card'
whitelisted_methods['rcore.api.lms.readiness_revoke_share'] = 'rcore.rlms.rlms.api.readiness.revoke_share'
override_whitelisted_methods['rcore.api.lms.readiness_revoke_share'] = 'rcore.rlms.rlms.api.readiness.revoke_share'
whitelisted_methods['rcore.api.lms.practice_queue'] = 'rcore.rlms.rlms.api.practice.practice_queue'
override_whitelisted_methods['rcore.api.lms.practice_queue'] = 'rcore.rlms.rlms.api.practice.practice_queue'
whitelisted_methods['rcore.api.lms.record_practice_attempt'] = 'rcore.rlms.rlms.api.practice.record_practice_attempt'
override_whitelisted_methods['rcore.api.lms.record_practice_attempt'] = 'rcore.rlms.rlms.api.practice.record_practice_attempt'
whitelisted_methods['rcore.api.lms.publish_practice_bank'] = 'rcore.rlms.rlms.api.practice.publish_practice_bank'
override_whitelisted_methods['rcore.api.lms.publish_practice_bank'] = 'rcore.rlms.rlms.api.practice.publish_practice_bank'
whitelisted_methods['rcore.api.lms.active_announcements'] = 'rcore.rlms.rlms.api.announcements.active_announcements'
override_whitelisted_methods['rcore.api.lms.active_announcements'] = 'rcore.rlms.rlms.api.announcements.active_announcements'
whitelisted_methods['rcore.api.lms.can_manage_announcements'] = 'rcore.rlms.rlms.api.announcements.can_manage_announcements'
override_whitelisted_methods['rcore.api.lms.can_manage_announcements'] = 'rcore.rlms.rlms.api.announcements.can_manage_announcements'
whitelisted_methods['rcore.api.lms.create_announcement'] = 'rcore.rlms.rlms.api.announcements.create_announcement'
override_whitelisted_methods['rcore.api.lms.create_announcement'] = 'rcore.rlms.rlms.api.announcements.create_announcement'
whitelisted_methods['rcore.api.lms.retire_announcement'] = 'rcore.rlms.rlms.api.announcements.retire_announcement'
override_whitelisted_methods['rcore.api.lms.retire_announcement'] = 'rcore.rlms.rlms.api.announcements.retire_announcement'
whitelisted_methods['rcore.api.lms.list_announcements'] = 'rcore.rlms.rlms.api.announcements.list_announcements'
override_whitelisted_methods['rcore.api.lms.list_announcements'] = 'rcore.rlms.rlms.api.announcements.list_announcements'
whitelisted_methods['rcore.api.lms.my_term_report'] = 'rcore.rlms.rlms.api.term_report.my_term_report'
override_whitelisted_methods['rcore.api.lms.my_term_report'] = 'rcore.rlms.rlms.api.term_report.my_term_report'
whitelisted_methods['rcore.api.lms.partner_term_report'] = 'rcore.rlms.rlms.api.term_report.partner_term_report'
override_whitelisted_methods['rcore.api.lms.partner_term_report'] = 'rcore.rlms.rlms.api.term_report.partner_term_report'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', 'in', ['LMS Course', 'Course Chapter', 'Course Lesson', 'LMS Enrollment', 'LMS Course Progress', 'LMS Video Watch Duration', 'LMS Lesson Quiz Result', 'LMS Partner Link', 'LMS Attendance Event', 'LMS Partner Alert', 'LMS Student Profile', 'LMS Subscription Period', 'LMS Billing Record', 'LMS Plan', 'LMS Skills Index', 'LMS Homework Question', 'LMS Tutor Catalog', 'LMS League Membership', 'LMS Knowledge Bites Index', 'LMS Readiness Share', 'LMS Practice Item Bank', 'LMS Practice Attempt', 'LMS Announcement']]]})

# --- Module: comms ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.notification.get_notification_count'] = 'rcore.comms.api.notification.get_notification_count'
override_whitelisted_methods['rcore.api.notification.get_notification_count'] = 'rcore.comms.api.notification.get_notification_count'
whitelisted_methods['rcore.api.notification.get_user_notifications'] = 'rcore.comms.api.notification.get_user_notifications'
override_whitelisted_methods['rcore.api.notification.get_user_notifications'] = 'rcore.comms.api.notification.get_user_notifications'
whitelisted_methods['rcore.api.notification.get_notification_settings'] = 'rcore.comms.api.notification.get_notification_settings'
override_whitelisted_methods['rcore.api.notification.get_notification_settings'] = 'rcore.comms.api.notification.get_notification_settings'
whitelisted_methods['rcore.api.notification.mark_notification_logs_as_read'] = 'rcore.comms.api.notification.mark_notification_logs_as_read'
override_whitelisted_methods['rcore.api.notification.mark_notification_logs_as_read'] = 'rcore.comms.api.notification.mark_notification_logs_as_read'
whitelisted_methods['rcore.api.notification.read_all_notifications'] = 'rcore.comms.api.notification.read_all_notifications'
override_whitelisted_methods['rcore.api.notification.read_all_notifications'] = 'rcore.comms.api.notification.read_all_notifications'
whitelisted_methods['rcore.api.notification.read_one_notification'] = 'rcore.comms.api.notification.read_one_notification'
override_whitelisted_methods['rcore.api.notification.read_one_notification'] = 'rcore.comms.api.notification.read_one_notification'
whitelisted_methods['rcore.api.notification.update_notification_settings'] = 'rcore.comms.api.notification.update_notification_settings'
override_whitelisted_methods['rcore.api.notification.update_notification_settings'] = 'rcore.comms.api.notification.update_notification_settings'
whitelisted_methods['rcore.api.whatsapp.flow_endpoint'] = 'rcore.comms.api.whatsapp.flow_endpoint'
override_whitelisted_methods['rcore.api.whatsapp.flow_endpoint'] = 'rcore.comms.api.whatsapp.flow_endpoint'
whitelisted_methods['rcore.api.whatsapp.hook'] = 'rcore.comms.api.whatsapp.hook'
override_whitelisted_methods['rcore.api.whatsapp.hook'] = 'rcore.comms.api.whatsapp.hook'
whitelisted_methods['rcore.api.notification.get_default_sms_payload'] = 'rcore.comms.api.notification.get_default_sms_payload'
override_whitelisted_methods['rcore.api.notification.get_default_sms_payload'] = 'rcore.comms.api.notification.get_default_sms_payload'
whitelisted_methods['rcore.api.notification.send_push_notification'] = 'rcore.comms.api.notification.send_push_notification'
override_whitelisted_methods['rcore.api.notification.send_push_notification'] = 'rcore.comms.api.notification.send_push_notification'
whitelisted_methods['rcore.tenant.api.get_welcome_email_details'] = 'rcore.comms.comms.get_welcome_email_details.get_welcome_email_details'
override_whitelisted_methods['rcore.tenant.api.get_welcome_email_details'] = 'rcore.comms.comms.get_welcome_email_details.get_welcome_email_details'
whitelisted_methods['rcore.tenant.api.save_email_settings'] = 'rcore.comms.comms.save_email_settings.save_email_settings'
override_whitelisted_methods['rcore.tenant.api.save_email_settings'] = 'rcore.comms.comms.save_email_settings.save_email_settings'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Device Token']]})
fixtures.append({'dt': 'Email Template', 'filters': [['name', 'in', ['New User Welcome', 'Support User Expired', 'Critical Tenant Creation Failed', 'Critical Tenant Setup Failed']]]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Meeting']]})

# --- Module: wallet ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.payment.create_transaction'] = 'rcore.wallet.api.payment.create_transaction'
override_whitelisted_methods['rcore.api.payment.create_transaction'] = 'rcore.wallet.api.payment.create_transaction'
whitelisted_methods['rcore.api.payment.delete_card'] = 'rcore.wallet.api.payment.delete_card'
override_whitelisted_methods['rcore.api.payment.delete_card'] = 'rcore.wallet.api.payment.delete_card'
whitelisted_methods['rcore.api.payment.get_saved_cards'] = 'rcore.wallet.api.payment.get_saved_cards'
override_whitelisted_methods['rcore.api.payment.get_saved_cards'] = 'rcore.wallet.api.payment.get_saved_cards'
whitelisted_methods['rcore.api.payment.process_direct_card_payment'] = 'rcore.wallet.api.payment.process_direct_card_payment'
override_whitelisted_methods['rcore.api.payment.process_direct_card_payment'] = 'rcore.wallet.api.payment.process_direct_card_payment'
whitelisted_methods['rcore.api.payment.process_token_payment'] = 'rcore.wallet.api.payment.process_token_payment'
override_whitelisted_methods['rcore.api.payment.process_token_payment'] = 'rcore.wallet.api.payment.process_token_payment'
whitelisted_methods['rcore.api.payment.process_wallet_top_up'] = 'rcore.wallet.api.payment.process_wallet_top_up'
override_whitelisted_methods['rcore.api.payment.process_wallet_top_up'] = 'rcore.wallet.api.payment.process_wallet_top_up'
whitelisted_methods['rcore.api.payment.tip_process'] = 'rcore.wallet.api.payment.tip_process'
override_whitelisted_methods['rcore.api.payment.tip_process'] = 'rcore.wallet.api.payment.tip_process'
whitelisted_methods['rcore.api.payment.tokenize_card'] = 'rcore.wallet.api.payment.tokenize_card'
override_whitelisted_methods['rcore.api.payment.tokenize_card'] = 'rcore.wallet.api.payment.tokenize_card'
whitelisted_methods['rcore.api.payment.create_order_transaction'] = 'rcore.wallet.api.payment.create_order_transaction'
override_whitelisted_methods['rcore.api.payment.create_order_transaction'] = 'rcore.wallet.api.payment.create_order_transaction'
whitelisted_methods['rcore.api.payment.delete_payfast_card'] = 'rcore.wallet.api.payment.delete_payfast_card'
override_whitelisted_methods['rcore.api.payment.delete_payfast_card'] = 'rcore.wallet.api.payment.delete_payfast_card'
whitelisted_methods['rcore.api.payment.flutterwave_callback'] = 'rcore.wallet.api.payment.flutterwave_callback'
override_whitelisted_methods['rcore.api.payment.flutterwave_callback'] = 'rcore.wallet.api.payment.flutterwave_callback'
whitelisted_methods['rcore.api.payment.get_payfast_settings'] = 'rcore.wallet.api.payment.get_payfast_settings'
override_whitelisted_methods['rcore.api.payment.get_payfast_settings'] = 'rcore.wallet.api.payment.get_payfast_settings'
whitelisted_methods['rcore.api.payment.get_payment_gateways'] = 'rcore.wallet.api.payment.get_payment_gateways'
override_whitelisted_methods['rcore.api.payment.get_payment_gateways'] = 'rcore.wallet.api.payment.get_payment_gateways'
whitelisted_methods['rcore.api.payment.get_saved_payfast_cards'] = 'rcore.wallet.api.payment.get_saved_payfast_cards'
override_whitelisted_methods['rcore.api.payment.get_saved_payfast_cards'] = 'rcore.wallet.api.payment.get_saved_payfast_cards'
whitelisted_methods['rcore.api.payment.handle_payfast_callback'] = 'rcore.wallet.api.payment.handle_payfast_callback'
override_whitelisted_methods['rcore.api.payment.handle_payfast_callback'] = 'rcore.wallet.api.payment.handle_payfast_callback'
whitelisted_methods['rcore.api.payment.handle_paypal_callback'] = 'rcore.wallet.api.payment.handle_paypal_callback'
override_whitelisted_methods['rcore.api.payment.handle_paypal_callback'] = 'rcore.wallet.api.payment.handle_paypal_callback'
whitelisted_methods['rcore.api.payment.handle_paystack_callback'] = 'rcore.wallet.api.payment.handle_paystack_callback'
override_whitelisted_methods['rcore.api.payment.handle_paystack_callback'] = 'rcore.wallet.api.payment.handle_paystack_callback'
whitelisted_methods['rcore.api.payment.handle_stripe_webhook'] = 'rcore.wallet.api.payment.handle_stripe_webhook'
override_whitelisted_methods['rcore.api.payment.handle_stripe_webhook'] = 'rcore.wallet.api.payment.handle_stripe_webhook'
whitelisted_methods['rcore.api.payment.initiate_flutterwave_payment'] = 'rcore.wallet.api.payment.initiate_flutterwave_payment'
override_whitelisted_methods['rcore.api.payment.initiate_flutterwave_payment'] = 'rcore.wallet.api.payment.initiate_flutterwave_payment'
whitelisted_methods['rcore.api.payment.initiate_paypal_payment'] = 'rcore.wallet.api.payment.initiate_paypal_payment'
override_whitelisted_methods['rcore.api.payment.initiate_paypal_payment'] = 'rcore.wallet.api.payment.initiate_paypal_payment'
whitelisted_methods['rcore.api.payment.initiate_paystack_payment'] = 'rcore.wallet.api.payment.initiate_paystack_payment'
override_whitelisted_methods['rcore.api.payment.initiate_paystack_payment'] = 'rcore.wallet.api.payment.initiate_paystack_payment'
whitelisted_methods['rcore.api.payment.log_payment_payload'] = 'rcore.wallet.api.payment.log_payment_payload'
override_whitelisted_methods['rcore.api.payment.log_payment_payload'] = 'rcore.wallet.api.payment.log_payment_payload'
whitelisted_methods['rcore.api.payment.process_payfast_token_payment'] = 'rcore.wallet.api.payment.process_payfast_token_payment'
override_whitelisted_methods['rcore.api.payment.process_payfast_token_payment'] = 'rcore.wallet.api.payment.process_payfast_token_payment'
whitelisted_methods['rcore.api.payment.process_wallet_payment'] = 'rcore.wallet.api.payment.process_wallet_payment'
override_whitelisted_methods['rcore.api.payment.process_wallet_payment'] = 'rcore.wallet.api.payment.process_wallet_payment'
whitelisted_methods['rcore.api.payment.save_payfast_card'] = 'rcore.wallet.api.payment.save_payfast_card'
override_whitelisted_methods['rcore.api.payment.save_payfast_card'] = 'rcore.wallet.api.payment.save_payfast_card'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Wallet']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Saved Card']]})

# --- Module: gateways ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('all', [])
for _t in ['rcore.gateways.doctype.razorpay_settings.razorpay_settings.capture_payment']:
    if _t not in scheduler_events['all']: scheduler_events['all'].append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['frappe.website.doctype.web_form.web_form.accept'] = 'rcore.gateways.overrides.payment_webform.accept'
override_whitelisted_methods['frappe.website.doctype.web_form.web_form.accept'] = 'rcore.gateways.overrides.payment_webform.accept'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'PayFast Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Paystack Settings']]})

# --- Module: delivery ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('hourly', [])
for _t in ['rcore.delivery.providers.lifecycle.process_due_pickup_releases']:
    if _t not in scheduler_events['hourly']: scheduler_events['hourly'].append(_t)
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('daily', [])
for _t in ['rcore.delivery.providers.lifecycle.sweep_orphan_pickup_locations']:
    if _t not in scheduler_events['daily']: scheduler_events['daily'].append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.parcel.add_parcel_review'] = 'rcore.delivery.api.parcel.parcel.add_parcel_review'
override_whitelisted_methods['rcore.api.parcel.add_parcel_review'] = 'rcore.delivery.api.parcel.parcel.add_parcel_review'
whitelisted_methods['rcore.api.parcel.create_parcel_order'] = 'rcore.delivery.api.parcel.parcel.create_parcel_order'
override_whitelisted_methods['rcore.api.parcel.create_parcel_order'] = 'rcore.delivery.api.parcel.parcel.create_parcel_order'
whitelisted_methods['rcore.api.delivery.get_driver_location'] = 'rcore.delivery.api.delivery.delivery.get_driver_location'
override_whitelisted_methods['rcore.api.delivery.get_driver_location'] = 'rcore.delivery.api.delivery.delivery.get_driver_location'
whitelisted_methods['rcore.api.parcel.calculate_price'] = 'rcore.delivery.api.parcel.parcel.calculate_price'
override_whitelisted_methods['rcore.api.parcel.calculate_price'] = 'rcore.delivery.api.parcel.parcel.calculate_price'
whitelisted_methods['rcore.api.parcel.get_types'] = 'rcore.delivery.api.parcel.parcel.get_types'
override_whitelisted_methods['rcore.api.parcel.get_types'] = 'rcore.delivery.api.parcel.parcel.get_types'
whitelisted_methods['rcore.api.delivery.check_delivery_zone'] = 'rcore.delivery.api.delivery.delivery.check_delivery_zone'
override_whitelisted_methods['rcore.api.delivery.check_delivery_zone'] = 'rcore.delivery.api.delivery.delivery.check_delivery_zone'
whitelisted_methods['rcore.api.delivery.get_delivery_point'] = 'rcore.delivery.api.delivery.delivery.get_delivery_point'
override_whitelisted_methods['rcore.api.delivery.get_delivery_point'] = 'rcore.delivery.api.delivery.delivery.get_delivery_point'
whitelisted_methods['rcore.api.delivery.get_delivery_points'] = 'rcore.delivery.api.delivery.delivery.get_delivery_points'
override_whitelisted_methods['rcore.api.delivery.get_delivery_points'] = 'rcore.delivery.api.delivery.delivery.get_delivery_points'
whitelisted_methods['rcore.api.delivery.get_delivery_zone_by_shop'] = 'rcore.delivery.api.delivery.delivery.get_delivery_zone_by_shop'
override_whitelisted_methods['rcore.api.delivery.get_delivery_zone_by_shop'] = 'rcore.delivery.api.delivery.delivery.get_delivery_zone_by_shop'
whitelisted_methods['rcore.api.delivery_man.get_banned_shops'] = 'rcore.delivery.api.delivery_man.delivery_man.get_banned_shops'
override_whitelisted_methods['rcore.api.delivery_man.get_banned_shops'] = 'rcore.delivery.api.delivery_man.delivery_man.get_banned_shops'
whitelisted_methods['rcore.api.delivery_man.get_deliveryman_delivery_zones'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_delivery_zones'
override_whitelisted_methods['rcore.api.delivery_man.get_deliveryman_delivery_zones'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_delivery_zones'
whitelisted_methods['rcore.api.delivery_man.get_deliveryman_order_report'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_order_report'
override_whitelisted_methods['rcore.api.delivery_man.get_deliveryman_order_report'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_order_report'
whitelisted_methods['rcore.api.delivery_man.get_deliveryman_orders'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_orders'
override_whitelisted_methods['rcore.api.delivery_man.get_deliveryman_orders'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_orders'
whitelisted_methods['rcore.api.delivery_man.get_deliveryman_parcel_orders'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_parcel_orders'
override_whitelisted_methods['rcore.api.delivery_man.get_deliveryman_parcel_orders'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_parcel_orders'
whitelisted_methods['rcore.api.delivery_man.get_deliveryman_settings'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_settings'
override_whitelisted_methods['rcore.api.delivery_man.get_deliveryman_settings'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_settings'
whitelisted_methods['rcore.api.delivery_man.get_deliveryman_statistics'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_statistics'
override_whitelisted_methods['rcore.api.delivery_man.get_deliveryman_statistics'] = 'rcore.delivery.api.delivery_man.delivery_man.get_deliveryman_statistics'
whitelisted_methods['rcore.api.delivery_man.get_payment_to_partners'] = 'rcore.delivery.api.delivery_man.delivery_man.get_payment_to_partners'
override_whitelisted_methods['rcore.api.delivery_man.get_payment_to_partners'] = 'rcore.delivery.api.delivery_man.delivery_man.get_payment_to_partners'
whitelisted_methods['rcore.api.delivery_man.update_deliveryman_settings'] = 'rcore.delivery.api.delivery_man.delivery_man.update_deliveryman_settings'
override_whitelisted_methods['rcore.api.delivery_man.update_deliveryman_settings'] = 'rcore.delivery.api.delivery_man.delivery_man.update_deliveryman_settings'
whitelisted_methods['rcore.api.parcel.get_parcel_orders'] = 'rcore.delivery.api.parcel.parcel.get_parcel_orders'
override_whitelisted_methods['rcore.api.parcel.get_parcel_orders'] = 'rcore.delivery.api.parcel.parcel.get_parcel_orders'
whitelisted_methods['rcore.api.parcel.get_user_parcel_order'] = 'rcore.delivery.api.parcel.parcel.get_user_parcel_order'
override_whitelisted_methods['rcore.api.parcel.get_user_parcel_order'] = 'rcore.delivery.api.parcel.parcel.get_user_parcel_order'
whitelisted_methods['rcore.api.parcel.update_parcel_status'] = 'rcore.delivery.api.parcel.parcel.update_parcel_status'
override_whitelisted_methods['rcore.api.parcel.update_parcel_status'] = 'rcore.delivery.api.parcel.parcel.update_parcel_status'
whitelisted_methods['rcore.api.parcel_option.create_parcel_option'] = 'rcore.delivery.api.parcel_option.parcel_option.create_parcel_option'
override_whitelisted_methods['rcore.api.parcel_option.create_parcel_option'] = 'rcore.delivery.api.parcel_option.parcel_option.create_parcel_option'
whitelisted_methods['rcore.api.parcel_option.delete_parcel_option'] = 'rcore.delivery.api.parcel_option.parcel_option.delete_parcel_option'
override_whitelisted_methods['rcore.api.parcel_option.delete_parcel_option'] = 'rcore.delivery.api.parcel_option.parcel_option.delete_parcel_option'
whitelisted_methods['rcore.api.parcel_option.get_parcel_options'] = 'rcore.delivery.api.parcel_option.parcel_option.get_parcel_options'
override_whitelisted_methods['rcore.api.parcel_option.get_parcel_options'] = 'rcore.delivery.api.parcel_option.parcel_option.get_parcel_options'
whitelisted_methods['rcore.api.parcel_option.update_parcel_option'] = 'rcore.delivery.api.parcel_option.parcel_option.update_parcel_option'
override_whitelisted_methods['rcore.api.parcel_option.update_parcel_option'] = 'rcore.delivery.api.parcel_option.parcel_option.update_parcel_option'
whitelisted_methods['rcore.api.parcel_order_setting.create_parcel_order_setting'] = 'rcore.delivery.api.parcel_order_setting.parcel_order_setting.create_parcel_order_setting'
override_whitelisted_methods['rcore.api.parcel_order_setting.create_parcel_order_setting'] = 'rcore.delivery.api.parcel_order_setting.parcel_order_setting.create_parcel_order_setting'
whitelisted_methods['rcore.api.parcel_order_setting.delete_parcel_order_setting'] = 'rcore.delivery.api.parcel_order_setting.parcel_order_setting.delete_parcel_order_setting'
override_whitelisted_methods['rcore.api.parcel_order_setting.delete_parcel_order_setting'] = 'rcore.delivery.api.parcel_order_setting.parcel_order_setting.delete_parcel_order_setting'
whitelisted_methods['rcore.api.parcel_order_setting.get_parcel_order_settings'] = 'rcore.delivery.api.parcel_order_setting.parcel_order_setting.get_parcel_order_settings'
override_whitelisted_methods['rcore.api.parcel_order_setting.get_parcel_order_settings'] = 'rcore.delivery.api.parcel_order_setting.parcel_order_setting.get_parcel_order_settings'
whitelisted_methods['rcore.api.parcel_order_setting.update_parcel_order_setting'] = 'rcore.delivery.api.parcel_order_setting.parcel_order_setting.update_parcel_order_setting'
override_whitelisted_methods['rcore.api.parcel_order_setting.update_parcel_order_setting'] = 'rcore.delivery.api.parcel_order_setting.parcel_order_setting.update_parcel_order_setting'
whitelisted_methods['rcore.api.intercity.get_intercity_quote'] = 'rcore.delivery.api.intercity.intercity.get_intercity_quote'
override_whitelisted_methods['rcore.api.intercity.get_intercity_quote'] = 'rcore.delivery.api.intercity.intercity.get_intercity_quote'
whitelisted_methods['rcore.api.intercity.cancel_intercity_shipment'] = 'rcore.delivery.api.intercity.intercity.cancel_intercity_shipment'
override_whitelisted_methods['rcore.api.intercity.cancel_intercity_shipment'] = 'rcore.delivery.api.intercity.intercity.cancel_intercity_shipment'
whitelisted_methods['rcore.api.intercity.get_intercity_tracking'] = 'rcore.delivery.api.intercity.intercity.get_intercity_tracking'
override_whitelisted_methods['rcore.api.intercity.get_intercity_tracking'] = 'rcore.delivery.api.intercity.intercity.get_intercity_tracking'
whitelisted_methods['rcore.api.intercity.intercity_webhook'] = 'rcore.delivery.api.intercity.intercity.intercity_webhook'
override_whitelisted_methods['rcore.api.intercity.intercity_webhook'] = 'rcore.delivery.api.intercity.intercity.intercity_webhook'
whitelisted_methods['rcore.api.driver_parcel.add_parcel_order_review'] = 'rcore.delivery.api.driver_parcel.driver_parcel.add_parcel_order_review'
override_whitelisted_methods['rcore.api.driver_parcel.add_parcel_order_review'] = 'rcore.delivery.api.driver_parcel.driver_parcel.add_parcel_order_review'
whitelisted_methods['rcore.api.driver_parcel.attach_parcel_order_to_me'] = 'rcore.delivery.api.driver_parcel.driver_parcel.attach_parcel_order_to_me'
override_whitelisted_methods['rcore.api.driver_parcel.attach_parcel_order_to_me'] = 'rcore.delivery.api.driver_parcel.driver_parcel.attach_parcel_order_to_me'
whitelisted_methods['rcore.api.driver_parcel.confirm_parcel_cod_collection'] = 'rcore.delivery.api.driver_parcel.driver_parcel.confirm_parcel_cod_collection'
override_whitelisted_methods['rcore.api.driver_parcel.confirm_parcel_cod_collection'] = 'rcore.delivery.api.driver_parcel.driver_parcel.confirm_parcel_cod_collection'
whitelisted_methods['rcore.api.driver_parcel.set_current_parcel_order'] = 'rcore.delivery.api.driver_parcel.driver_parcel.set_current_parcel_order'
override_whitelisted_methods['rcore.api.driver_parcel.set_current_parcel_order'] = 'rcore.delivery.api.driver_parcel.driver_parcel.set_current_parcel_order'
whitelisted_methods['rcore.api.driver_parcel.update_driver_parcel_order_status'] = 'rcore.delivery.api.driver_parcel.driver_parcel.update_driver_parcel_order_status'
override_whitelisted_methods['rcore.api.driver_parcel.update_driver_parcel_order_status'] = 'rcore.delivery.api.driver_parcel.driver_parcel.update_driver_parcel_order_status'
whitelisted_methods['rcore.api.dispatch_route.get_my_dispatch_route'] = 'rcore.delivery.api.dispatch_route.dispatch_route.get_my_dispatch_route'
override_whitelisted_methods['rcore.api.dispatch_route.get_my_dispatch_route'] = 'rcore.delivery.api.dispatch_route.dispatch_route.get_my_dispatch_route'
whitelisted_methods['rcore.api.dispatch_route.complete_dispatch_stop'] = 'rcore.delivery.api.dispatch_route.dispatch_route.complete_dispatch_stop'
override_whitelisted_methods['rcore.api.dispatch_route.complete_dispatch_stop'] = 'rcore.delivery.api.dispatch_route.dispatch_route.complete_dispatch_stop'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Parcel Order']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Deliveryman Profile']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Tip']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Dispatch Route']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Dispatch Route Stop']]})

# --- Module: map ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.driver_order.attach_order_to_me'] = 'rcore.map.api.driver_order.driver_order.attach_order_to_me'
override_whitelisted_methods['rcore.api.driver_order.attach_order_to_me'] = 'rcore.map.api.driver_order.driver_order.attach_order_to_me'
whitelisted_methods['rcore.api.driver_order.confirm_cod_collection'] = 'rcore.map.api.driver_order.driver_order.confirm_cod_collection'
override_whitelisted_methods['rcore.api.driver_order.confirm_cod_collection'] = 'rcore.map.api.driver_order.driver_order.confirm_cod_collection'
whitelisted_methods['rcore.api.driver_order.convert_cod_to_credit'] = 'rcore.map.api.driver_order.driver_order.convert_cod_to_credit'
override_whitelisted_methods['rcore.api.driver_order.convert_cod_to_credit'] = 'rcore.map.api.driver_order.driver_order.convert_cod_to_credit'
whitelisted_methods['rcore.api.driver_order.get_driver_orders_paginate'] = 'rcore.map.api.driver_order.driver_order.get_driver_orders_paginate'
override_whitelisted_methods['rcore.api.driver_order.get_driver_orders_paginate'] = 'rcore.map.api.driver_order.driver_order.get_driver_orders_paginate'
whitelisted_methods['rcore.api.driver_order.get_driver_route'] = 'rcore.map.api.driver_order.driver_order.get_driver_route'
override_whitelisted_methods['rcore.api.driver_order.get_driver_route'] = 'rcore.map.api.driver_order.driver_order.get_driver_route'
whitelisted_methods['rcore.api.driver_order.set_current_order'] = 'rcore.map.api.driver_order.driver_order.set_current_order'
override_whitelisted_methods['rcore.api.driver_order.set_current_order'] = 'rcore.map.api.driver_order.driver_order.set_current_order'
whitelisted_methods['rcore.api.driver_order.update_driver_order_status'] = 'rcore.map.api.driver_order.driver_order.update_driver_order_status'
override_whitelisted_methods['rcore.api.driver_order.update_driver_order_status'] = 'rcore.map.api.driver_order.driver_order.update_driver_order_status'
whitelisted_methods['rcore.api.driver_order.upload_order_image'] = 'rcore.map.api.driver_order.driver_order.upload_order_image'
override_whitelisted_methods['rcore.api.driver_order.upload_order_image'] = 'rcore.map.api.driver_order.driver_order.upload_order_image'
whitelisted_methods['rcore.api.driver.update_location'] = 'rcore.map.api.driver.driver.update_location'
override_whitelisted_methods['rcore.api.driver.update_location'] = 'rcore.map.api.driver.driver.update_location'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Driver Location']]})

# --- Module: zones ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.delivery_zone.check_delivery_availability'] = 'rcore.zones.api.delivery_zone.delivery_zone.check_delivery_availability'
override_whitelisted_methods['rcore.api.delivery_zone.check_delivery_availability'] = 'rcore.zones.api.delivery_zone.delivery_zone.check_delivery_availability'
whitelisted_methods['rcore.api.delivery_zone.create_delivery_zone'] = 'rcore.zones.api.delivery_zone.delivery_zone.create_delivery_zone'
override_whitelisted_methods['rcore.api.delivery_zone.create_delivery_zone'] = 'rcore.zones.api.delivery_zone.delivery_zone.create_delivery_zone'
whitelisted_methods['rcore.api.delivery_zone.delete_delivery_zone'] = 'rcore.zones.api.delivery_zone.delivery_zone.delete_delivery_zone'
override_whitelisted_methods['rcore.api.delivery_zone.delete_delivery_zone'] = 'rcore.zones.api.delivery_zone.delivery_zone.delete_delivery_zone'
whitelisted_methods['rcore.api.delivery_zone.get_shop_delivery_zones'] = 'rcore.zones.api.delivery_zone.delivery_zone.get_shop_delivery_zones'
override_whitelisted_methods['rcore.api.delivery_zone.get_shop_delivery_zones'] = 'rcore.zones.api.delivery_zone.delivery_zone.get_shop_delivery_zones'
whitelisted_methods['rcore.api.delivery_zone.update_delivery_zone'] = 'rcore.zones.api.delivery_zone.delivery_zone.update_delivery_zone'
override_whitelisted_methods['rcore.api.delivery_zone.update_delivery_zone'] = 'rcore.zones.api.delivery_zone.delivery_zone.update_delivery_zone'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Delivery Zone']]})

# --- Module: booking ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.booking.cancel_my_booking'] = 'rcore.booking.api.booking.cancel_my_booking'
override_whitelisted_methods['rcore.api.booking.cancel_my_booking'] = 'rcore.booking.api.booking.cancel_my_booking'
whitelisted_methods['rcore.api.booking.create_booking'] = 'rcore.booking.api.booking.create_booking'
override_whitelisted_methods['rcore.api.booking.create_booking'] = 'rcore.booking.api.booking.create_booking'
whitelisted_methods['rcore.api.booking.create_booking_slot'] = 'rcore.booking.api.booking.create_booking_slot'
override_whitelisted_methods['rcore.api.booking.create_booking_slot'] = 'rcore.booking.api.booking.create_booking_slot'
whitelisted_methods['rcore.api.booking.create_reservation'] = 'rcore.booking.api.booking.create_reservation'
override_whitelisted_methods['rcore.api.booking.create_reservation'] = 'rcore.booking.api.booking.create_reservation'
whitelisted_methods['rcore.api.booking.create_shop_section'] = 'rcore.booking.api.booking.create_shop_section'
override_whitelisted_methods['rcore.api.booking.create_shop_section'] = 'rcore.booking.api.booking.create_shop_section'
whitelisted_methods['rcore.api.booking.create_table'] = 'rcore.booking.api.booking.create_table'
override_whitelisted_methods['rcore.api.booking.create_table'] = 'rcore.booking.api.booking.create_table'
whitelisted_methods['rcore.api.booking.create_user_booking'] = 'rcore.booking.api.booking.create_user_booking'
override_whitelisted_methods['rcore.api.booking.create_user_booking'] = 'rcore.booking.api.booking.create_user_booking'
whitelisted_methods['rcore.api.booking.delete_booking'] = 'rcore.booking.api.booking.delete_booking'
override_whitelisted_methods['rcore.api.booking.delete_booking'] = 'rcore.booking.api.booking.delete_booking'
whitelisted_methods['rcore.api.booking.delete_booking_slot'] = 'rcore.booking.api.booking.delete_booking_slot'
override_whitelisted_methods['rcore.api.booking.delete_booking_slot'] = 'rcore.booking.api.booking.delete_booking_slot'
whitelisted_methods['rcore.api.booking.delete_shop_section'] = 'rcore.booking.api.booking.delete_shop_section'
override_whitelisted_methods['rcore.api.booking.delete_shop_section'] = 'rcore.booking.api.booking.delete_shop_section'
whitelisted_methods['rcore.api.booking.delete_table'] = 'rcore.booking.api.booking.delete_table'
override_whitelisted_methods['rcore.api.booking.delete_table'] = 'rcore.booking.api.booking.delete_table'
whitelisted_methods['rcore.api.booking.get_booking'] = 'rcore.booking.api.booking.get_booking'
override_whitelisted_methods['rcore.api.booking.get_booking'] = 'rcore.booking.api.booking.get_booking'
whitelisted_methods['rcore.api.booking.get_booking_slots'] = 'rcore.booking.api.booking.get_booking_slots'
override_whitelisted_methods['rcore.api.booking.get_booking_slots'] = 'rcore.booking.api.booking.get_booking_slots'
whitelisted_methods['rcore.api.booking.get_my_bookings'] = 'rcore.booking.api.booking.get_my_bookings'
override_whitelisted_methods['rcore.api.booking.get_my_bookings'] = 'rcore.booking.api.booking.get_my_bookings'
whitelisted_methods['rcore.api.booking.get_my_reservations'] = 'rcore.booking.api.booking.get_my_reservations'
override_whitelisted_methods['rcore.api.booking.get_my_reservations'] = 'rcore.booking.api.booking.get_my_reservations'
whitelisted_methods['rcore.api.booking.get_shop_bookings'] = 'rcore.booking.api.booking.get_shop_bookings'
override_whitelisted_methods['rcore.api.booking.get_shop_bookings'] = 'rcore.booking.api.booking.get_shop_bookings'
whitelisted_methods['rcore.api.booking.get_shop_reservations'] = 'rcore.booking.api.booking.get_shop_reservations'
override_whitelisted_methods['rcore.api.booking.get_shop_reservations'] = 'rcore.booking.api.booking.get_shop_reservations'
whitelisted_methods['rcore.api.booking.get_shop_section'] = 'rcore.booking.api.booking.get_shop_section'
override_whitelisted_methods['rcore.api.booking.get_shop_section'] = 'rcore.booking.api.booking.get_shop_section'
whitelisted_methods['rcore.api.booking.get_shop_sections_for_booking'] = 'rcore.booking.api.booking.get_shop_sections_for_booking'
override_whitelisted_methods['rcore.api.booking.get_shop_sections_for_booking'] = 'rcore.booking.api.booking.get_shop_sections_for_booking'
whitelisted_methods['rcore.api.booking.get_shop_user_bookings'] = 'rcore.booking.api.booking.get_shop_user_bookings'
override_whitelisted_methods['rcore.api.booking.get_shop_user_bookings'] = 'rcore.booking.api.booking.get_shop_user_bookings'
whitelisted_methods['rcore.api.booking.get_table'] = 'rcore.booking.api.booking.get_table'
override_whitelisted_methods['rcore.api.booking.get_table'] = 'rcore.booking.api.booking.get_table'
whitelisted_methods['rcore.api.booking.get_tables_for_section'] = 'rcore.booking.api.booking.get_tables_for_section'
override_whitelisted_methods['rcore.api.booking.get_tables_for_section'] = 'rcore.booking.api.booking.get_tables_for_section'
whitelisted_methods['rcore.api.booking.get_user_bookings'] = 'rcore.booking.api.booking.get_user_bookings'
override_whitelisted_methods['rcore.api.booking.get_user_bookings'] = 'rcore.booking.api.booking.get_user_bookings'
whitelisted_methods['rcore.api.booking.manage_shop_booking_closed_dates'] = 'rcore.booking.api.booking.manage_shop_booking_closed_dates'
override_whitelisted_methods['rcore.api.booking.manage_shop_booking_closed_dates'] = 'rcore.booking.api.booking.manage_shop_booking_closed_dates'
whitelisted_methods['rcore.api.booking.manage_shop_booking_working_days'] = 'rcore.booking.api.booking.manage_shop_booking_working_days'
override_whitelisted_methods['rcore.api.booking.manage_shop_booking_working_days'] = 'rcore.booking.api.booking.manage_shop_booking_working_days'
whitelisted_methods['rcore.api.booking.update_booking'] = 'rcore.booking.api.booking.update_booking'
override_whitelisted_methods['rcore.api.booking.update_booking'] = 'rcore.booking.api.booking.update_booking'
whitelisted_methods['rcore.api.booking.update_booking_slot'] = 'rcore.booking.api.booking.update_booking_slot'
override_whitelisted_methods['rcore.api.booking.update_booking_slot'] = 'rcore.booking.api.booking.update_booking_slot'
whitelisted_methods['rcore.api.booking.update_reservation_status'] = 'rcore.booking.api.booking.update_reservation_status'
override_whitelisted_methods['rcore.api.booking.update_reservation_status'] = 'rcore.booking.api.booking.update_reservation_status'
whitelisted_methods['rcore.api.booking.update_shop_section'] = 'rcore.booking.api.booking.update_shop_section'
override_whitelisted_methods['rcore.api.booking.update_shop_section'] = 'rcore.booking.api.booking.update_shop_section'
whitelisted_methods['rcore.api.booking.update_shop_user_booking_status'] = 'rcore.booking.api.booking.update_shop_user_booking_status'
override_whitelisted_methods['rcore.api.booking.update_shop_user_booking_status'] = 'rcore.booking.api.booking.update_shop_user_booking_status'
whitelisted_methods['rcore.api.booking.update_table'] = 'rcore.booking.api.booking.update_table'
override_whitelisted_methods['rcore.api.booking.update_table'] = 'rcore.booking.api.booking.update_table'
whitelisted_methods['rcore.api.booking.update_user_booking_status'] = 'rcore.booking.api.booking.update_user_booking_status'
override_whitelisted_methods['rcore.api.booking.update_user_booking_status'] = 'rcore.booking.api.booking.update_user_booking_status'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Booking']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Table']]})

# --- Module: kitchen ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.cook.get_cook_order_report'] = 'rcore.kitchen.api.cook.get_cook_order_report'
override_whitelisted_methods['rcore.api.cook.get_cook_order_report'] = 'rcore.kitchen.api.cook.get_cook_order_report'
whitelisted_methods['rcore.api.cook.get_cook_orders'] = 'rcore.kitchen.api.cook.get_cook_orders'
override_whitelisted_methods['rcore.api.cook.get_cook_orders'] = 'rcore.kitchen.api.cook.get_cook_orders'
whitelisted_methods['rcore.api.receipt.get_receipt'] = 'rcore.kitchen.api.receipt.get_receipt'
override_whitelisted_methods['rcore.api.receipt.get_receipt'] = 'rcore.kitchen.api.receipt.get_receipt'
whitelisted_methods['rcore.api.receipt.get_receipts'] = 'rcore.kitchen.api.receipt.get_receipts'
override_whitelisted_methods['rcore.api.receipt.get_receipts'] = 'rcore.kitchen.api.receipt.get_receipts'
whitelisted_methods['rcore.api.waiter.get_waiter_order_report'] = 'rcore.kitchen.api.waiter.get_waiter_order_report'
override_whitelisted_methods['rcore.api.waiter.get_waiter_order_report'] = 'rcore.kitchen.api.waiter.get_waiter_order_report'
whitelisted_methods['rcore.api.waiter.get_waiter_orders'] = 'rcore.kitchen.api.waiter.get_waiter_orders'
override_whitelisted_methods['rcore.api.waiter.get_waiter_orders'] = 'rcore.kitchen.api.waiter.get_waiter_orders'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Kitchen']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Receipt']]})

# --- Module: merchants ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.shop.check_cashback'] = 'rcore.merchants.api.shop.check_cashback'
override_whitelisted_methods['rcore.api.shop.check_cashback'] = 'rcore.merchants.api.shop.check_cashback'
whitelisted_methods['rcore.api.shop.create_shop'] = 'rcore.merchants.api.shop.create_shop'
override_whitelisted_methods['rcore.api.shop.create_shop'] = 'rcore.merchants.api.shop.create_shop'
whitelisted_methods['rcore.api.shop.get_nearby_shops'] = 'rcore.merchants.api.shop.get_nearby_shops'
override_whitelisted_methods['rcore.api.shop.get_nearby_shops'] = 'rcore.merchants.api.shop.get_nearby_shops'
whitelisted_methods['rcore.api.shop.get_shops'] = 'rcore.merchants.api.shop.get_shops'
override_whitelisted_methods['rcore.api.shop.get_shops'] = 'rcore.merchants.api.shop.get_shops'
whitelisted_methods['rcore.api.shop.get_shops_by_ids'] = 'rcore.merchants.api.shop.get_shops_by_ids'
override_whitelisted_methods['rcore.api.shop.get_shops_by_ids'] = 'rcore.merchants.api.shop.get_shops_by_ids'
whitelisted_methods['rcore.api.shop.get_shops_recommend'] = 'rcore.merchants.api.shop.get_shops_recommend'
override_whitelisted_methods['rcore.api.shop.get_shops_recommend'] = 'rcore.merchants.api.shop.get_shops_recommend'
whitelisted_methods['rcore.api.seller_bonus.get_seller_bonuses'] = 'rcore.merchants.api.seller_bonus.get_seller_bonuses'
override_whitelisted_methods['rcore.api.seller_bonus.get_seller_bonuses'] = 'rcore.merchants.api.seller_bonus.get_seller_bonuses'
whitelisted_methods['rcore.api.seller_customer_management.get_seller_customer_addresses'] = 'rcore.merchants.api.seller_customer_management.get_seller_customer_addresses'
override_whitelisted_methods['rcore.api.seller_customer_management.get_seller_customer_addresses'] = 'rcore.merchants.api.seller_customer_management.get_seller_customer_addresses'
whitelisted_methods['rcore.api.seller_customer_management.get_seller_request_models'] = 'rcore.merchants.api.seller_customer_management.get_seller_request_models'
override_whitelisted_methods['rcore.api.seller_customer_management.get_seller_request_models'] = 'rcore.merchants.api.seller_customer_management.get_seller_request_models'
whitelisted_methods['rcore.api.seller_delivery_zone.check_delivery_fee'] = 'rcore.merchants.api.seller_delivery_zone.check_delivery_fee'
override_whitelisted_methods['rcore.api.seller_delivery_zone.check_delivery_fee'] = 'rcore.merchants.api.seller_delivery_zone.check_delivery_fee'
whitelisted_methods['rcore.api.seller_delivery_zone.create_seller_delivery_zone'] = 'rcore.merchants.api.seller_delivery_zone.create_seller_delivery_zone'
override_whitelisted_methods['rcore.api.seller_delivery_zone.create_seller_delivery_zone'] = 'rcore.merchants.api.seller_delivery_zone.create_seller_delivery_zone'
whitelisted_methods['rcore.api.seller_delivery_zone.delete_seller_delivery_zone'] = 'rcore.merchants.api.seller_delivery_zone.delete_seller_delivery_zone'
override_whitelisted_methods['rcore.api.seller_delivery_zone.delete_seller_delivery_zone'] = 'rcore.merchants.api.seller_delivery_zone.delete_seller_delivery_zone'
whitelisted_methods['rcore.api.seller_delivery_zone.get_seller_delivery_zone'] = 'rcore.merchants.api.seller_delivery_zone.get_seller_delivery_zone'
override_whitelisted_methods['rcore.api.seller_delivery_zone.get_seller_delivery_zone'] = 'rcore.merchants.api.seller_delivery_zone.get_seller_delivery_zone'
whitelisted_methods['rcore.api.seller_delivery_zone.get_seller_delivery_zones'] = 'rcore.merchants.api.seller_delivery_zone.get_seller_delivery_zones'
override_whitelisted_methods['rcore.api.seller_delivery_zone.get_seller_delivery_zones'] = 'rcore.merchants.api.seller_delivery_zone.get_seller_delivery_zones'
whitelisted_methods['rcore.api.seller_delivery_zone.update_seller_delivery_zone'] = 'rcore.merchants.api.seller_delivery_zone.update_seller_delivery_zone'
override_whitelisted_methods['rcore.api.seller_delivery_zone.update_seller_delivery_zone'] = 'rcore.merchants.api.seller_delivery_zone.update_seller_delivery_zone'
whitelisted_methods['rcore.api.seller_invites.get_seller_invites'] = 'rcore.merchants.api.seller_invites.get_seller_invites'
override_whitelisted_methods['rcore.api.seller_invites.get_seller_invites'] = 'rcore.merchants.api.seller_invites.get_seller_invites'
whitelisted_methods['rcore.api.seller_logistics.adjust_seller_inventory'] = 'rcore.merchants.api.seller_logistics.adjust_seller_inventory'
override_whitelisted_methods['rcore.api.seller_logistics.adjust_seller_inventory'] = 'rcore.merchants.api.seller_logistics.adjust_seller_inventory'
whitelisted_methods['rcore.api.seller_logistics.get_seller_delivery_man_delivery_zones'] = 'rcore.merchants.api.seller_logistics.get_seller_delivery_man_delivery_zones'
override_whitelisted_methods['rcore.api.seller_logistics.get_seller_delivery_man_delivery_zones'] = 'rcore.merchants.api.seller_logistics.get_seller_delivery_man_delivery_zones'
whitelisted_methods['rcore.api.seller_marketing.create_seller_banner'] = 'rcore.merchants.api.seller_marketing.create_seller_banner'
override_whitelisted_methods['rcore.api.seller_marketing.create_seller_banner'] = 'rcore.merchants.api.seller_marketing.create_seller_banner'
whitelisted_methods['rcore.api.seller_marketing.create_seller_coupon'] = 'rcore.merchants.api.seller_marketing.create_seller_coupon'
override_whitelisted_methods['rcore.api.seller_marketing.create_seller_coupon'] = 'rcore.merchants.api.seller_marketing.create_seller_coupon'
whitelisted_methods['rcore.api.seller_marketing.create_seller_discount'] = 'rcore.merchants.api.seller_marketing.create_seller_discount'
override_whitelisted_methods['rcore.api.seller_marketing.create_seller_discount'] = 'rcore.merchants.api.seller_marketing.create_seller_discount'
whitelisted_methods['rcore.api.seller_marketing.delete_seller_banner'] = 'rcore.merchants.api.seller_marketing.delete_seller_banner'
override_whitelisted_methods['rcore.api.seller_marketing.delete_seller_banner'] = 'rcore.merchants.api.seller_marketing.delete_seller_banner'
whitelisted_methods['rcore.api.seller_marketing.delete_seller_coupon'] = 'rcore.merchants.api.seller_marketing.delete_seller_coupon'
override_whitelisted_methods['rcore.api.seller_marketing.delete_seller_coupon'] = 'rcore.merchants.api.seller_marketing.delete_seller_coupon'
whitelisted_methods['rcore.api.seller_marketing.delete_seller_discount'] = 'rcore.merchants.api.seller_marketing.delete_seller_discount'
override_whitelisted_methods['rcore.api.seller_marketing.delete_seller_discount'] = 'rcore.merchants.api.seller_marketing.delete_seller_discount'
whitelisted_methods['rcore.api.seller_marketing.get_ads_packages'] = 'rcore.merchants.api.seller_marketing.get_ads_packages'
override_whitelisted_methods['rcore.api.seller_marketing.get_ads_packages'] = 'rcore.merchants.api.seller_marketing.get_ads_packages'
whitelisted_methods['rcore.api.seller_marketing.get_seller_banners'] = 'rcore.merchants.api.seller_marketing.get_seller_banners'
override_whitelisted_methods['rcore.api.seller_marketing.get_seller_banners'] = 'rcore.merchants.api.seller_marketing.get_seller_banners'
whitelisted_methods['rcore.api.seller_marketing.get_seller_coupons'] = 'rcore.merchants.api.seller_marketing.get_seller_coupons'
override_whitelisted_methods['rcore.api.seller_marketing.get_seller_coupons'] = 'rcore.merchants.api.seller_marketing.get_seller_coupons'
whitelisted_methods['rcore.api.seller_marketing.get_seller_discounts'] = 'rcore.merchants.api.seller_marketing.get_seller_discounts'
override_whitelisted_methods['rcore.api.seller_marketing.get_seller_discounts'] = 'rcore.merchants.api.seller_marketing.get_seller_discounts'
whitelisted_methods['rcore.api.seller_marketing.get_seller_shop_ads_packages'] = 'rcore.merchants.api.seller_marketing.get_seller_shop_ads_packages'
override_whitelisted_methods['rcore.api.seller_marketing.get_seller_shop_ads_packages'] = 'rcore.merchants.api.seller_marketing.get_seller_shop_ads_packages'
whitelisted_methods['rcore.api.seller_marketing.purchase_shop_ads_package'] = 'rcore.merchants.api.seller_marketing.purchase_shop_ads_package'
override_whitelisted_methods['rcore.api.seller_marketing.purchase_shop_ads_package'] = 'rcore.merchants.api.seller_marketing.purchase_shop_ads_package'
whitelisted_methods['rcore.api.seller_marketing.update_seller_banner'] = 'rcore.merchants.api.seller_marketing.update_seller_banner'
override_whitelisted_methods['rcore.api.seller_marketing.update_seller_banner'] = 'rcore.merchants.api.seller_marketing.update_seller_banner'
whitelisted_methods['rcore.api.seller_marketing.update_seller_coupon'] = 'rcore.merchants.api.seller_marketing.update_seller_coupon'
override_whitelisted_methods['rcore.api.seller_marketing.update_seller_coupon'] = 'rcore.merchants.api.seller_marketing.update_seller_coupon'
whitelisted_methods['rcore.api.seller_marketing.update_seller_discount'] = 'rcore.merchants.api.seller_marketing.update_seller_discount'
override_whitelisted_methods['rcore.api.seller_marketing.update_seller_discount'] = 'rcore.merchants.api.seller_marketing.update_seller_discount'
whitelisted_methods['rcore.api.seller_operations.adjust_seller_inventory'] = 'rcore.merchants.api.seller_operations.adjust_seller_inventory'
override_whitelisted_methods['rcore.api.seller_operations.adjust_seller_inventory'] = 'rcore.merchants.api.seller_operations.adjust_seller_inventory'
whitelisted_methods['rcore.api.seller_operations.create_seller_combo'] = 'rcore.merchants.api.seller_operations.create_seller_combo'
override_whitelisted_methods['rcore.api.seller_operations.create_seller_combo'] = 'rcore.merchants.api.seller_operations.create_seller_combo'
whitelisted_methods['rcore.api.seller_operations.create_seller_kitchen'] = 'rcore.merchants.api.seller_operations.create_seller_kitchen'
override_whitelisted_methods['rcore.api.seller_operations.create_seller_kitchen'] = 'rcore.merchants.api.seller_operations.create_seller_kitchen'
whitelisted_methods['rcore.api.seller_operations.create_seller_menu'] = 'rcore.merchants.api.seller_operations.create_seller_menu'
override_whitelisted_methods['rcore.api.seller_operations.create_seller_menu'] = 'rcore.merchants.api.seller_operations.create_seller_menu'
whitelisted_methods['rcore.api.seller_operations.create_seller_receipt'] = 'rcore.merchants.api.seller_operations.create_seller_receipt'
override_whitelisted_methods['rcore.api.seller_operations.create_seller_receipt'] = 'rcore.merchants.api.seller_operations.create_seller_receipt'
whitelisted_methods['rcore.api.seller_operations.delete_seller_combo'] = 'rcore.merchants.api.seller_operations.delete_seller_combo'
override_whitelisted_methods['rcore.api.seller_operations.delete_seller_combo'] = 'rcore.merchants.api.seller_operations.delete_seller_combo'
whitelisted_methods['rcore.api.seller_operations.delete_seller_kitchen'] = 'rcore.merchants.api.seller_operations.delete_seller_kitchen'
override_whitelisted_methods['rcore.api.seller_operations.delete_seller_kitchen'] = 'rcore.merchants.api.seller_operations.delete_seller_kitchen'
whitelisted_methods['rcore.api.seller_operations.delete_seller_menu'] = 'rcore.merchants.api.seller_operations.delete_seller_menu'
override_whitelisted_methods['rcore.api.seller_operations.delete_seller_menu'] = 'rcore.merchants.api.seller_operations.delete_seller_menu'
whitelisted_methods['rcore.api.seller_operations.delete_seller_receipt'] = 'rcore.merchants.api.seller_operations.delete_seller_receipt'
override_whitelisted_methods['rcore.api.seller_operations.delete_seller_receipt'] = 'rcore.merchants.api.seller_operations.delete_seller_receipt'
whitelisted_methods['rcore.api.seller_operations.get_seller_combo'] = 'rcore.merchants.api.seller_operations.get_seller_combo'
override_whitelisted_methods['rcore.api.seller_operations.get_seller_combo'] = 'rcore.merchants.api.seller_operations.get_seller_combo'
whitelisted_methods['rcore.api.seller_operations.get_seller_combos'] = 'rcore.merchants.api.seller_operations.get_seller_combos'
override_whitelisted_methods['rcore.api.seller_operations.get_seller_combos'] = 'rcore.merchants.api.seller_operations.get_seller_combos'
whitelisted_methods['rcore.api.seller_operations.get_seller_inventory_items'] = 'rcore.merchants.api.seller_operations.get_seller_inventory_items'
override_whitelisted_methods['rcore.api.seller_operations.get_seller_inventory_items'] = 'rcore.merchants.api.seller_operations.get_seller_inventory_items'
whitelisted_methods['rcore.api.seller_operations.get_seller_kitchens'] = 'rcore.merchants.api.seller_operations.get_seller_kitchens'
override_whitelisted_methods['rcore.api.seller_operations.get_seller_kitchens'] = 'rcore.merchants.api.seller_operations.get_seller_kitchens'
whitelisted_methods['rcore.api.seller_operations.get_seller_menu'] = 'rcore.merchants.api.seller_operations.get_seller_menu'
override_whitelisted_methods['rcore.api.seller_operations.get_seller_menu'] = 'rcore.merchants.api.seller_operations.get_seller_menu'
whitelisted_methods['rcore.api.seller_operations.get_seller_menus'] = 'rcore.merchants.api.seller_operations.get_seller_menus'
override_whitelisted_methods['rcore.api.seller_operations.get_seller_menus'] = 'rcore.merchants.api.seller_operations.get_seller_menus'
whitelisted_methods['rcore.api.seller_operations.get_seller_sections'] = 'rcore.merchants.api.seller_operations.get_seller_sections'
override_whitelisted_methods['rcore.api.seller_operations.get_seller_sections'] = 'rcore.merchants.api.seller_operations.get_seller_sections'
whitelisted_methods['rcore.api.seller_operations.get_seller_tables'] = 'rcore.merchants.api.seller_operations.get_seller_tables'
override_whitelisted_methods['rcore.api.seller_operations.get_seller_tables'] = 'rcore.merchants.api.seller_operations.get_seller_tables'
whitelisted_methods['rcore.api.seller_operations.get_seller_receipts'] = 'rcore.merchants.api.seller_operations.get_seller_receipts'
override_whitelisted_methods['rcore.api.seller_operations.get_seller_receipts'] = 'rcore.merchants.api.seller_operations.get_seller_receipts'
whitelisted_methods['rcore.api.seller_operations.update_seller_combo'] = 'rcore.merchants.api.seller_operations.update_seller_combo'
override_whitelisted_methods['rcore.api.seller_operations.update_seller_combo'] = 'rcore.merchants.api.seller_operations.update_seller_combo'
whitelisted_methods['rcore.api.seller_operations.update_seller_kitchen'] = 'rcore.merchants.api.seller_operations.update_seller_kitchen'
override_whitelisted_methods['rcore.api.seller_operations.update_seller_kitchen'] = 'rcore.merchants.api.seller_operations.update_seller_kitchen'
whitelisted_methods['rcore.api.seller_operations.update_seller_menu'] = 'rcore.merchants.api.seller_operations.update_seller_menu'
override_whitelisted_methods['rcore.api.seller_operations.update_seller_menu'] = 'rcore.merchants.api.seller_operations.update_seller_menu'
whitelisted_methods['rcore.api.seller_operations.update_seller_receipt'] = 'rcore.merchants.api.seller_operations.update_seller_receipt'
override_whitelisted_methods['rcore.api.seller_operations.update_seller_receipt'] = 'rcore.merchants.api.seller_operations.update_seller_receipt'
whitelisted_methods['rcore.api.seller_order.get_seller_order_details'] = 'rcore.merchants.api.seller_order.get_seller_order_details'
override_whitelisted_methods['rcore.api.seller_order.get_seller_order_details'] = 'rcore.merchants.api.seller_order.get_seller_order_details'
whitelisted_methods['rcore.api.seller_order.get_seller_order_refunds'] = 'rcore.merchants.api.seller_order.get_seller_order_refunds'
override_whitelisted_methods['rcore.api.seller_order.get_seller_order_refunds'] = 'rcore.merchants.api.seller_order.get_seller_order_refunds'
whitelisted_methods['rcore.api.seller_order.get_seller_orders'] = 'rcore.merchants.api.seller_order.get_seller_orders'
override_whitelisted_methods['rcore.api.seller_order.get_seller_orders'] = 'rcore.merchants.api.seller_order.get_seller_orders'
whitelisted_methods['rcore.api.seller_order.get_seller_reviews'] = 'rcore.merchants.api.seller_order.get_seller_reviews'
override_whitelisted_methods['rcore.api.seller_order.get_seller_reviews'] = 'rcore.merchants.api.seller_order.get_seller_reviews'
whitelisted_methods['rcore.api.seller_order.update_seller_order_refund'] = 'rcore.merchants.api.seller_order.update_seller_order_refund'
override_whitelisted_methods['rcore.api.seller_order.update_seller_order_refund'] = 'rcore.merchants.api.seller_order.update_seller_order_refund'
whitelisted_methods['rcore.api.seller_order.update_seller_order_status'] = 'rcore.merchants.api.seller_order.update_seller_order_status'
override_whitelisted_methods['rcore.api.seller_order.update_seller_order_status'] = 'rcore.merchants.api.seller_order.update_seller_order_status'
whitelisted_methods['rcore.api.seller_payout.get_seller_payouts'] = 'rcore.merchants.api.seller_payout.get_seller_payouts'
override_whitelisted_methods['rcore.api.seller_payout.get_seller_payouts'] = 'rcore.merchants.api.seller_payout.get_seller_payouts'
whitelisted_methods['rcore.api.seller_product.create_seller_brand'] = 'rcore.merchants.api.seller_product.create_seller_brand'
override_whitelisted_methods['rcore.api.seller_product.create_seller_brand'] = 'rcore.merchants.api.seller_product.create_seller_brand'
whitelisted_methods['rcore.api.seller_product.create_seller_category'] = 'rcore.merchants.api.seller_product.create_seller_category'
override_whitelisted_methods['rcore.api.seller_product.create_seller_category'] = 'rcore.merchants.api.seller_product.create_seller_category'
whitelisted_methods['rcore.api.seller_product.create_seller_extra_group'] = 'rcore.merchants.api.seller_product.create_seller_extra_group'
override_whitelisted_methods['rcore.api.seller_product.create_seller_extra_group'] = 'rcore.merchants.api.seller_product.create_seller_extra_group'
whitelisted_methods['rcore.api.seller_product.create_seller_extra_value'] = 'rcore.merchants.api.seller_product.create_seller_extra_value'
override_whitelisted_methods['rcore.api.seller_product.create_seller_extra_value'] = 'rcore.merchants.api.seller_product.create_seller_extra_value'
whitelisted_methods['rcore.api.seller_product.create_seller_product'] = 'rcore.merchants.api.seller_product.create_seller_product'
override_whitelisted_methods['rcore.api.seller_product.create_seller_product'] = 'rcore.merchants.api.seller_product.create_seller_product'
whitelisted_methods['rcore.api.seller_product.create_seller_tag'] = 'rcore.merchants.api.seller_product.create_seller_tag'
override_whitelisted_methods['rcore.api.seller_product.create_seller_tag'] = 'rcore.merchants.api.seller_product.create_seller_tag'
whitelisted_methods['rcore.api.seller_product.create_seller_unit'] = 'rcore.merchants.api.seller_product.create_seller_unit'
override_whitelisted_methods['rcore.api.seller_product.create_seller_unit'] = 'rcore.merchants.api.seller_product.create_seller_unit'
whitelisted_methods['rcore.api.seller_product.create_product'] = 'rcore.merchants.api.seller_product.create_product'
override_whitelisted_methods['rcore.api.seller_product.create_product'] = 'rcore.merchants.api.seller_product.create_product'
whitelisted_methods['rcore.api.seller_product.delete_seller_brand'] = 'rcore.merchants.api.seller_product.delete_seller_brand'
override_whitelisted_methods['rcore.api.seller_product.delete_seller_brand'] = 'rcore.merchants.api.seller_product.delete_seller_brand'
whitelisted_methods['rcore.api.seller_product.delete_seller_category'] = 'rcore.merchants.api.seller_product.delete_seller_category'
override_whitelisted_methods['rcore.api.seller_product.delete_seller_category'] = 'rcore.merchants.api.seller_product.delete_seller_category'
whitelisted_methods['rcore.api.seller_product.delete_seller_extra_group'] = 'rcore.merchants.api.seller_product.delete_seller_extra_group'
override_whitelisted_methods['rcore.api.seller_product.delete_seller_extra_group'] = 'rcore.merchants.api.seller_product.delete_seller_extra_group'
whitelisted_methods['rcore.api.seller_product.delete_seller_extra_value'] = 'rcore.merchants.api.seller_product.delete_seller_extra_value'
override_whitelisted_methods['rcore.api.seller_product.delete_seller_extra_value'] = 'rcore.merchants.api.seller_product.delete_seller_extra_value'
whitelisted_methods['rcore.api.seller_product.delete_seller_product'] = 'rcore.merchants.api.seller_product.delete_seller_product'
override_whitelisted_methods['rcore.api.seller_product.delete_seller_product'] = 'rcore.merchants.api.seller_product.delete_seller_product'
whitelisted_methods['rcore.api.seller_product.delete_seller_tag'] = 'rcore.merchants.api.seller_product.delete_seller_tag'
override_whitelisted_methods['rcore.api.seller_product.delete_seller_tag'] = 'rcore.merchants.api.seller_product.delete_seller_tag'
whitelisted_methods['rcore.api.seller_product.delete_seller_unit'] = 'rcore.merchants.api.seller_product.delete_seller_unit'
override_whitelisted_methods['rcore.api.seller_product.delete_seller_unit'] = 'rcore.merchants.api.seller_product.delete_seller_unit'
whitelisted_methods['rcore.api.seller_product.get_seller_brands'] = 'rcore.merchants.api.seller_product.get_seller_brands'
override_whitelisted_methods['rcore.api.seller_product.get_seller_brands'] = 'rcore.merchants.api.seller_product.get_seller_brands'
whitelisted_methods['rcore.api.seller_product.get_seller_categories'] = 'rcore.merchants.api.seller_product.get_seller_categories'
override_whitelisted_methods['rcore.api.seller_product.get_seller_categories'] = 'rcore.merchants.api.seller_product.get_seller_categories'
whitelisted_methods['rcore.api.seller_product.get_seller_extra_groups'] = 'rcore.merchants.api.seller_product.get_seller_extra_groups'
override_whitelisted_methods['rcore.api.seller_product.get_seller_extra_groups'] = 'rcore.merchants.api.seller_product.get_seller_extra_groups'
whitelisted_methods['rcore.api.seller_product.get_seller_extra_values'] = 'rcore.merchants.api.seller_product.get_seller_extra_values'
override_whitelisted_methods['rcore.api.seller_product.get_seller_extra_values'] = 'rcore.merchants.api.seller_product.get_seller_extra_values'
whitelisted_methods['rcore.api.seller_product.get_seller_products'] = 'rcore.merchants.api.seller_product.get_seller_products'
override_whitelisted_methods['rcore.api.seller_product.get_seller_products'] = 'rcore.merchants.api.seller_product.get_seller_products'
whitelisted_methods['rcore.api.seller_product.get_seller_tags'] = 'rcore.merchants.api.seller_product.get_seller_tags'
override_whitelisted_methods['rcore.api.seller_product.get_seller_tags'] = 'rcore.merchants.api.seller_product.get_seller_tags'
whitelisted_methods['rcore.api.seller_product.get_seller_units'] = 'rcore.merchants.api.seller_product.get_seller_units'
override_whitelisted_methods['rcore.api.seller_product.get_seller_units'] = 'rcore.merchants.api.seller_product.get_seller_units'
whitelisted_methods['rcore.api.seller_product.update_seller_brand'] = 'rcore.merchants.api.seller_product.update_seller_brand'
override_whitelisted_methods['rcore.api.seller_product.update_seller_brand'] = 'rcore.merchants.api.seller_product.update_seller_brand'
whitelisted_methods['rcore.api.seller_product.update_seller_category'] = 'rcore.merchants.api.seller_product.update_seller_category'
override_whitelisted_methods['rcore.api.seller_product.update_seller_category'] = 'rcore.merchants.api.seller_product.update_seller_category'
whitelisted_methods['rcore.api.seller_product.update_seller_extra_group'] = 'rcore.merchants.api.seller_product.update_seller_extra_group'
override_whitelisted_methods['rcore.api.seller_product.update_seller_extra_group'] = 'rcore.merchants.api.seller_product.update_seller_extra_group'
whitelisted_methods['rcore.api.seller_product.update_seller_extra_value'] = 'rcore.merchants.api.seller_product.update_seller_extra_value'
override_whitelisted_methods['rcore.api.seller_product.update_seller_extra_value'] = 'rcore.merchants.api.seller_product.update_seller_extra_value'
whitelisted_methods['rcore.api.seller_product.update_seller_product'] = 'rcore.merchants.api.seller_product.update_seller_product'
override_whitelisted_methods['rcore.api.seller_product.update_seller_product'] = 'rcore.merchants.api.seller_product.update_seller_product'
whitelisted_methods['rcore.api.seller_product.update_seller_tag'] = 'rcore.merchants.api.seller_product.update_seller_tag'
override_whitelisted_methods['rcore.api.seller_product.update_seller_tag'] = 'rcore.merchants.api.seller_product.update_seller_tag'
whitelisted_methods['rcore.api.seller_product.update_seller_unit'] = 'rcore.merchants.api.seller_product.update_seller_unit'
override_whitelisted_methods['rcore.api.seller_product.update_seller_unit'] = 'rcore.merchants.api.seller_product.update_seller_unit'
whitelisted_methods['rcore.api.seller_report.get_order_report'] = 'rcore.merchants.api.seller_report.seller_report.get_order_report'
override_whitelisted_methods['rcore.api.seller_report.get_order_report'] = 'rcore.merchants.api.seller_report.seller_report.get_order_report'
whitelisted_methods['rcore.api.seller_report.get_order_report_paginate'] = 'rcore.merchants.api.seller_report.seller_report.get_order_report_paginate'
override_whitelisted_methods['rcore.api.seller_report.get_order_report_paginate'] = 'rcore.merchants.api.seller_report.seller_report.get_order_report_paginate'
whitelisted_methods['rcore.api.seller_reports.get_seller_sales_report'] = 'rcore.merchants.api.seller_reports.get_seller_sales_report'
override_whitelisted_methods['rcore.api.seller_reports.get_seller_sales_report'] = 'rcore.merchants.api.seller_reports.get_seller_sales_report'
whitelisted_methods['rcore.api.seller_reports.get_seller_statistics'] = 'rcore.merchants.api.seller_reports.get_seller_statistics'
override_whitelisted_methods['rcore.api.seller_reports.get_seller_statistics'] = 'rcore.merchants.api.seller_reports.get_seller_statistics'
whitelisted_methods['rcore.api.seller_shop.get_shop'] = 'rcore.merchants.api.seller_shop.get_shop'
override_whitelisted_methods['rcore.api.seller_shop.get_shop'] = 'rcore.merchants.api.seller_shop.get_shop'
whitelisted_methods['rcore.api.seller_shop.set_working_status'] = 'rcore.merchants.api.seller_shop.set_working_status'
override_whitelisted_methods['rcore.api.seller_shop.set_working_status'] = 'rcore.merchants.api.seller_shop.set_working_status'
whitelisted_methods['rcore.api.seller_shop.update_shop'] = 'rcore.merchants.api.seller_shop.update_shop'
override_whitelisted_methods['rcore.api.seller_shop.update_shop'] = 'rcore.merchants.api.seller_shop.update_shop'
whitelisted_methods['rcore.api.seller_shop_gallery.create_seller_shop_gallery'] = 'rcore.merchants.api.seller_shop_gallery.create_seller_shop_gallery'
override_whitelisted_methods['rcore.api.seller_shop_gallery.create_seller_shop_gallery'] = 'rcore.merchants.api.seller_shop_gallery.create_seller_shop_gallery'
whitelisted_methods['rcore.api.seller_shop_gallery.delete_seller_shop_gallery'] = 'rcore.merchants.api.seller_shop_gallery.delete_seller_shop_gallery'
override_whitelisted_methods['rcore.api.seller_shop_gallery.delete_seller_shop_gallery'] = 'rcore.merchants.api.seller_shop_gallery.delete_seller_shop_gallery'
whitelisted_methods['rcore.api.seller_shop_gallery.get_seller_shop_galleries'] = 'rcore.merchants.api.seller_shop_gallery.get_seller_shop_galleries'
override_whitelisted_methods['rcore.api.seller_shop_gallery.get_seller_shop_galleries'] = 'rcore.merchants.api.seller_shop_gallery.get_seller_shop_galleries'
whitelisted_methods['rcore.api.seller_shop_settings.add_seller_shop_closed_day'] = 'rcore.merchants.api.seller_shop_settings.add_seller_shop_closed_day'
override_whitelisted_methods['rcore.api.seller_shop_settings.add_seller_shop_closed_day'] = 'rcore.merchants.api.seller_shop_settings.add_seller_shop_closed_day'
whitelisted_methods['rcore.api.seller_shop_settings.add_shop_user'] = 'rcore.merchants.api.seller_shop_settings.add_shop_user'
override_whitelisted_methods['rcore.api.seller_shop_settings.add_shop_user'] = 'rcore.merchants.api.seller_shop_settings.add_shop_user'
whitelisted_methods['rcore.api.seller_shop_settings.create_seller_branch'] = 'rcore.merchants.api.seller_shop_settings.create_seller_branch'
override_whitelisted_methods['rcore.api.seller_shop_settings.create_seller_branch'] = 'rcore.merchants.api.seller_shop_settings.create_seller_branch'
whitelisted_methods['rcore.api.seller_shop_settings.delete_seller_branch'] = 'rcore.merchants.api.seller_shop_settings.delete_seller_branch'
override_whitelisted_methods['rcore.api.seller_shop_settings.delete_seller_branch'] = 'rcore.merchants.api.seller_shop_settings.delete_seller_branch'
whitelisted_methods['rcore.api.seller_shop_settings.delete_seller_shop_closed_day'] = 'rcore.merchants.api.seller_shop_settings.delete_seller_shop_closed_day'
override_whitelisted_methods['rcore.api.seller_shop_settings.delete_seller_shop_closed_day'] = 'rcore.merchants.api.seller_shop_settings.delete_seller_shop_closed_day'
whitelisted_methods['rcore.api.seller_shop_settings.get_seller_branches'] = 'rcore.merchants.api.seller_shop_settings.get_seller_branches'
override_whitelisted_methods['rcore.api.seller_shop_settings.get_seller_branches'] = 'rcore.merchants.api.seller_shop_settings.get_seller_branches'
whitelisted_methods['rcore.api.seller_shop_settings.get_seller_deliveryman_settings'] = 'rcore.merchants.api.seller_shop_settings.get_seller_deliveryman_settings'
override_whitelisted_methods['rcore.api.seller_shop_settings.get_seller_deliveryman_settings'] = 'rcore.merchants.api.seller_shop_settings.get_seller_deliveryman_settings'
whitelisted_methods['rcore.api.seller_shop_settings.get_seller_shop_closed_days'] = 'rcore.merchants.api.seller_shop_settings.get_seller_shop_closed_days'
override_whitelisted_methods['rcore.api.seller_shop_settings.get_seller_shop_closed_days'] = 'rcore.merchants.api.seller_shop_settings.get_seller_shop_closed_days'
whitelisted_methods['rcore.api.seller_shop_settings.get_seller_shop_working_days'] = 'rcore.merchants.api.seller_shop_settings.get_seller_shop_working_days'
override_whitelisted_methods['rcore.api.seller_shop_settings.get_seller_shop_working_days'] = 'rcore.merchants.api.seller_shop_settings.get_seller_shop_working_days'
whitelisted_methods['rcore.api.seller_shop_settings.get_shop_users'] = 'rcore.merchants.api.seller_shop_settings.get_shop_users'
override_whitelisted_methods['rcore.api.seller_shop_settings.get_shop_users'] = 'rcore.merchants.api.seller_shop_settings.get_shop_users'
whitelisted_methods['rcore.api.seller_shop_settings.remove_shop_user'] = 'rcore.merchants.api.seller_shop_settings.remove_shop_user'
override_whitelisted_methods['rcore.api.seller_shop_settings.remove_shop_user'] = 'rcore.merchants.api.seller_shop_settings.remove_shop_user'
whitelisted_methods['rcore.api.seller_shop_settings.update_seller_branch'] = 'rcore.merchants.api.seller_shop_settings.update_seller_branch'
override_whitelisted_methods['rcore.api.seller_shop_settings.update_seller_branch'] = 'rcore.merchants.api.seller_shop_settings.update_seller_branch'
whitelisted_methods['rcore.api.seller_shop_settings.update_seller_deliveryman_settings'] = 'rcore.merchants.api.seller_shop_settings.update_seller_deliveryman_settings'
override_whitelisted_methods['rcore.api.seller_shop_settings.update_seller_deliveryman_settings'] = 'rcore.merchants.api.seller_shop_settings.update_seller_deliveryman_settings'
whitelisted_methods['rcore.api.seller_shop_settings.update_seller_shop_working_days'] = 'rcore.merchants.api.seller_shop_settings.update_seller_shop_working_days'
override_whitelisted_methods['rcore.api.seller_shop_settings.update_seller_shop_working_days'] = 'rcore.merchants.api.seller_shop_settings.update_seller_shop_working_days'
whitelisted_methods['rcore.api.seller_story.create_seller_story'] = 'rcore.merchants.api.seller_story.create_seller_story'
override_whitelisted_methods['rcore.api.seller_story.create_seller_story'] = 'rcore.merchants.api.seller_story.create_seller_story'
whitelisted_methods['rcore.api.seller_story.delete_seller_story'] = 'rcore.merchants.api.seller_story.delete_seller_story'
override_whitelisted_methods['rcore.api.seller_story.delete_seller_story'] = 'rcore.merchants.api.seller_story.delete_seller_story'
whitelisted_methods['rcore.api.seller_story.get_seller_stories'] = 'rcore.merchants.api.seller_story.get_seller_stories'
override_whitelisted_methods['rcore.api.seller_story.get_seller_stories'] = 'rcore.merchants.api.seller_story.get_seller_stories'
whitelisted_methods['rcore.api.seller_story.update_seller_story'] = 'rcore.merchants.api.seller_story.update_seller_story'
override_whitelisted_methods['rcore.api.seller_story.update_seller_story'] = 'rcore.merchants.api.seller_story.update_seller_story'
whitelisted_methods['rcore.api.seller_transactions.get_seller_payment_to_partners'] = 'rcore.merchants.api.seller_transactions.get_seller_payment_to_partners'
override_whitelisted_methods['rcore.api.seller_transactions.get_seller_payment_to_partners'] = 'rcore.merchants.api.seller_transactions.get_seller_payment_to_partners'
whitelisted_methods['rcore.api.seller_transactions.get_seller_shop_payments'] = 'rcore.merchants.api.seller_transactions.get_seller_shop_payments'
override_whitelisted_methods['rcore.api.seller_transactions.get_seller_shop_payments'] = 'rcore.merchants.api.seller_transactions.get_seller_shop_payments'
whitelisted_methods['rcore.api.seller_transactions.get_seller_transactions'] = 'rcore.merchants.api.seller_transactions.get_seller_transactions'
override_whitelisted_methods['rcore.api.seller_transactions.get_seller_transactions'] = 'rcore.merchants.api.seller_transactions.get_seller_transactions'
whitelisted_methods['rcore.api.shop.check_driver_zone'] = 'rcore.merchants.api.shop.check_driver_zone'
override_whitelisted_methods['rcore.api.shop.check_driver_zone'] = 'rcore.merchants.api.shop.check_driver_zone'
whitelisted_methods['rcore.api.shop.get_shop_details'] = 'rcore.merchants.api.shop.get_shop_details'
override_whitelisted_methods['rcore.api.shop.get_shop_details'] = 'rcore.merchants.api.shop.get_shop_details'
whitelisted_methods['rcore.api.shop.get_shop_types'] = 'rcore.merchants.api.shop.get_shop_types'
override_whitelisted_methods['rcore.api.shop.get_shop_types'] = 'rcore.merchants.api.shop.get_shop_types'
whitelisted_methods['rcore.api.shop.search_shops'] = 'rcore.merchants.api.shop.search_shops'
override_whitelisted_methods['rcore.api.shop.search_shops'] = 'rcore.merchants.api.shop.search_shops'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Menu']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Seller']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Payout']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Shop']]})

# --- Module: orders ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('hourly', [])
for _t in ['rcore.orders.tasks.process_repeating_orders']:
    if _t not in scheduler_events['hourly']: scheduler_events['hourly'].append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.cart.change_status'] = 'rcore.orders.api.cart.change_status'
override_whitelisted_methods['rcore.api.cart.change_status'] = 'rcore.orders.api.cart.change_status'
whitelisted_methods['rcore.api.cart.create_and_cart'] = 'rcore.orders.api.cart.create_and_cart'
override_whitelisted_methods['rcore.api.cart.create_and_cart'] = 'rcore.orders.api.cart.create_and_cart'
whitelisted_methods['rcore.api.cart.create_cart'] = 'rcore.orders.api.cart.create_cart'
override_whitelisted_methods['rcore.api.cart.create_cart'] = 'rcore.orders.api.cart.create_cart'
whitelisted_methods['rcore.api.cart.delete_cart'] = 'rcore.orders.api.cart.delete_cart'
override_whitelisted_methods['rcore.api.cart.delete_cart'] = 'rcore.orders.api.cart.delete_cart'
whitelisted_methods['rcore.api.cart.delete_user'] = 'rcore.orders.api.cart.delete_user'
override_whitelisted_methods['rcore.api.cart.delete_user'] = 'rcore.orders.api.cart.delete_user'
whitelisted_methods['rcore.api.cart.get_cart_in_group'] = 'rcore.orders.api.cart.get_cart_in_group'
override_whitelisted_methods['rcore.api.cart.get_cart_in_group'] = 'rcore.orders.api.cart.get_cart_in_group'
whitelisted_methods['rcore.api.cart.insert_cart'] = 'rcore.orders.api.cart.insert_cart'
override_whitelisted_methods['rcore.api.cart.insert_cart'] = 'rcore.orders.api.cart.insert_cart'
whitelisted_methods['rcore.api.cart.insert_cart_with_group'] = 'rcore.orders.api.cart.insert_cart_with_group'
override_whitelisted_methods['rcore.api.cart.insert_cart_with_group'] = 'rcore.orders.api.cart.insert_cart_with_group'
whitelisted_methods['rcore.api.cart.join_order'] = 'rcore.orders.api.cart.join_order'
override_whitelisted_methods['rcore.api.cart.join_order'] = 'rcore.orders.api.cart.join_order'
whitelisted_methods['rcore.api.cart.remove_product_cart'] = 'rcore.orders.api.cart.remove_product_cart'
override_whitelisted_methods['rcore.api.cart.remove_product_cart'] = 'rcore.orders.api.cart.remove_product_cart'
whitelisted_methods['rcore.api.cart.add_to_cart'] = 'rcore.orders.api.cart.add_to_cart'
override_whitelisted_methods['rcore.api.cart.add_to_cart'] = 'rcore.orders.api.cart.add_to_cart'
whitelisted_methods['rcore.api.cart.get_cart'] = 'rcore.orders.api.cart.get_cart'
override_whitelisted_methods['rcore.api.cart.get_cart'] = 'rcore.orders.api.cart.get_cart'
whitelisted_methods['rcore.api.cart.remove_from_cart'] = 'rcore.orders.api.cart.remove_from_cart'
override_whitelisted_methods['rcore.api.cart.remove_from_cart'] = 'rcore.orders.api.cart.remove_from_cart'
whitelisted_methods['rcore.api.order.add_order_review'] = 'rcore.orders.api.order.add_order_review'
override_whitelisted_methods['rcore.api.order.add_order_review'] = 'rcore.orders.api.order.add_order_review'
whitelisted_methods['rcore.api.order.cancel_order'] = 'rcore.orders.api.order.cancel_order'
override_whitelisted_methods['rcore.api.order.cancel_order'] = 'rcore.orders.api.order.cancel_order'
whitelisted_methods['rcore.api.order.create_order'] = 'rcore.orders.api.order.create_order'
override_whitelisted_methods['rcore.api.order.create_order'] = 'rcore.orders.api.order.create_order'
whitelisted_methods['rcore.api.order.get_calculate'] = 'rcore.orders.api.order.get_calculate'
override_whitelisted_methods['rcore.api.order.get_calculate'] = 'rcore.orders.api.order.get_calculate'
whitelisted_methods['rcore.api.order.get_order_details'] = 'rcore.orders.api.order.get_order_details'
override_whitelisted_methods['rcore.api.order.get_order_details'] = 'rcore.orders.api.order.get_order_details'
whitelisted_methods['rcore.api.order.get_order_statuses'] = 'rcore.orders.api.order.get_order_statuses'
override_whitelisted_methods['rcore.api.order.get_order_statuses'] = 'rcore.orders.api.order.get_order_statuses'
whitelisted_methods['rcore.api.order.list_orders'] = 'rcore.orders.api.order.list_orders'
override_whitelisted_methods['rcore.api.order.list_orders'] = 'rcore.orders.api.order.list_orders'
whitelisted_methods['rcore.api.order.update_order_status'] = 'rcore.orders.api.order.update_order_status'
override_whitelisted_methods['rcore.api.order.update_order_status'] = 'rcore.orders.api.order.update_order_status'
whitelisted_methods['rcore.api.repeating_order.create_repeating_order'] = 'rcore.orders.api.repeating_order.create_repeating_order'
override_whitelisted_methods['rcore.api.repeating_order.create_repeating_order'] = 'rcore.orders.api.repeating_order.create_repeating_order'
whitelisted_methods['rcore.api.repeating_order.delete_repeating_order'] = 'rcore.orders.api.repeating_order.delete_repeating_order'
override_whitelisted_methods['rcore.api.repeating_order.delete_repeating_order'] = 'rcore.orders.api.repeating_order.delete_repeating_order'
whitelisted_methods['rcore.api.repeating_order.pause_repeating_order'] = 'rcore.orders.api.repeating_order.pause_repeating_order'
override_whitelisted_methods['rcore.api.repeating_order.pause_repeating_order'] = 'rcore.orders.api.repeating_order.pause_repeating_order'
whitelisted_methods['rcore.api.repeating_order.resume_repeating_order'] = 'rcore.orders.api.repeating_order.resume_repeating_order'
override_whitelisted_methods['rcore.api.repeating_order.resume_repeating_order'] = 'rcore.orders.api.repeating_order.resume_repeating_order'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Repeating Order']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Order']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Cart']]})

# --- Module: products ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.product.get_product_calculations'] = 'rcore.products.api.product.get_product_calculations'
override_whitelisted_methods['rcore.api.product.get_product_calculations'] = 'rcore.products.api.product.get_product_calculations'
whitelisted_methods['rcore.api.product.get_suggest_price'] = 'rcore.products.api.product.get_suggest_price'
override_whitelisted_methods['rcore.api.product.get_suggest_price'] = 'rcore.products.api.product.get_suggest_price'
whitelisted_methods['rcore.api.tag.get_tags'] = 'rcore.products.api.tag.get_tags'
override_whitelisted_methods['rcore.api.tag.get_tags'] = 'rcore.products.api.tag.get_tags'
whitelisted_methods['rcore.api.brand.create_brand'] = 'rcore.products.api.brand.create_brand'
override_whitelisted_methods['rcore.api.brand.create_brand'] = 'rcore.products.api.brand.create_brand'
whitelisted_methods['rcore.api.brand.delete_brand'] = 'rcore.products.api.brand.delete_brand'
override_whitelisted_methods['rcore.api.brand.delete_brand'] = 'rcore.products.api.brand.delete_brand'
whitelisted_methods['rcore.api.brand.get_brand_by_uuid'] = 'rcore.products.api.brand.get_brand_by_uuid'
override_whitelisted_methods['rcore.api.brand.get_brand_by_uuid'] = 'rcore.products.api.brand.get_brand_by_uuid'
whitelisted_methods['rcore.api.brand.get_brands'] = 'rcore.products.api.brand.get_brands'
override_whitelisted_methods['rcore.api.brand.get_brands'] = 'rcore.products.api.brand.get_brands'
whitelisted_methods['rcore.api.brand.update_brand'] = 'rcore.products.api.brand.update_brand'
override_whitelisted_methods['rcore.api.brand.update_brand'] = 'rcore.products.api.brand.update_brand'
whitelisted_methods['rcore.api.category.create_category'] = 'rcore.products.api.category.create_category'
override_whitelisted_methods['rcore.api.category.create_category'] = 'rcore.products.api.category.create_category'
whitelisted_methods['rcore.api.category.delete_category'] = 'rcore.products.api.category.delete_category'
override_whitelisted_methods['rcore.api.category.delete_category'] = 'rcore.products.api.category.delete_category'
whitelisted_methods['rcore.api.category.get_categories'] = 'rcore.products.api.category.get_categories'
override_whitelisted_methods['rcore.api.category.get_categories'] = 'rcore.products.api.category.get_categories'
whitelisted_methods['rcore.api.category.get_category_by_uuid'] = 'rcore.products.api.category.get_category_by_uuid'
override_whitelisted_methods['rcore.api.category.get_category_by_uuid'] = 'rcore.products.api.category.get_category_by_uuid'
whitelisted_methods['rcore.api.category.get_category_types'] = 'rcore.products.api.category.get_category_types'
override_whitelisted_methods['rcore.api.category.get_category_types'] = 'rcore.products.api.category.get_category_types'
whitelisted_methods['rcore.api.category.get_children_categories'] = 'rcore.products.api.category.get_children_categories'
override_whitelisted_methods['rcore.api.category.get_children_categories'] = 'rcore.products.api.category.get_children_categories'
whitelisted_methods['rcore.api.category.search_categories'] = 'rcore.products.api.category.search_categories'
override_whitelisted_methods['rcore.api.category.search_categories'] = 'rcore.products.api.category.search_categories'
whitelisted_methods['rcore.api.category.update_category'] = 'rcore.products.api.category.update_category'
override_whitelisted_methods['rcore.api.category.update_category'] = 'rcore.products.api.category.update_category'
whitelisted_methods['rcore.api.product.add_product_review'] = 'rcore.products.api.product.add_product_review'
override_whitelisted_methods['rcore.api.product.add_product_review'] = 'rcore.products.api.product.add_product_review'
whitelisted_methods['rcore.api.product.calculate_product_price'] = 'rcore.products.api.product.calculate_product_price'
override_whitelisted_methods['rcore.api.product.calculate_product_price'] = 'rcore.products.api.product.calculate_product_price'
whitelisted_methods['rcore.api.product.get_discounted_products'] = 'rcore.products.api.product.get_discounted_products'
override_whitelisted_methods['rcore.api.product.get_discounted_products'] = 'rcore.products.api.product.get_discounted_products'
whitelisted_methods['rcore.api.product.get_product_by_slug'] = 'rcore.products.api.product.get_product_by_slug'
override_whitelisted_methods['rcore.api.product.get_product_by_slug'] = 'rcore.products.api.product.get_product_by_slug'
whitelisted_methods['rcore.api.product.get_product_by_uuid'] = 'rcore.products.api.product.get_product_by_uuid'
override_whitelisted_methods['rcore.api.product.get_product_by_uuid'] = 'rcore.products.api.product.get_product_by_uuid'
whitelisted_methods['rcore.api.product.get_product_history'] = 'rcore.products.api.product.get_product_history'
override_whitelisted_methods['rcore.api.product.get_product_history'] = 'rcore.products.api.product.get_product_history'
whitelisted_methods['rcore.api.product.get_product_reviews'] = 'rcore.products.api.product.get_product_reviews'
override_whitelisted_methods['rcore.api.product.get_product_reviews'] = 'rcore.products.api.product.get_product_reviews'
whitelisted_methods['rcore.api.product.get_products'] = 'rcore.products.api.product.get_products'
override_whitelisted_methods['rcore.api.product.get_products'] = 'rcore.products.api.product.get_products'
whitelisted_methods['rcore.api.product.get_products_by_brand'] = 'rcore.products.api.product.get_products_by_brand'
override_whitelisted_methods['rcore.api.product.get_products_by_brand'] = 'rcore.products.api.product.get_products_by_brand'
whitelisted_methods['rcore.api.product.get_products_by_category'] = 'rcore.products.api.product.get_products_by_category'
override_whitelisted_methods['rcore.api.product.get_products_by_category'] = 'rcore.products.api.product.get_products_by_category'
whitelisted_methods['rcore.api.product.get_products_by_ids'] = 'rcore.products.api.product.get_products_by_ids'
override_whitelisted_methods['rcore.api.product.get_products_by_ids'] = 'rcore.products.api.product.get_products_by_ids'
whitelisted_methods['rcore.api.product.get_products_by_shop'] = 'rcore.products.api.product.get_products_by_shop'
override_whitelisted_methods['rcore.api.product.get_products_by_shop'] = 'rcore.products.api.product.get_products_by_shop'
whitelisted_methods['rcore.api.product.most_sold_products'] = 'rcore.products.api.product.most_sold_products'
override_whitelisted_methods['rcore.api.product.most_sold_products'] = 'rcore.products.api.product.most_sold_products'
whitelisted_methods['rcore.api.product.order_products_calculate'] = 'rcore.products.api.product.order_products_calculate'
override_whitelisted_methods['rcore.api.product.order_products_calculate'] = 'rcore.products.api.product.order_products_calculate'
whitelisted_methods['rcore.api.product.products_search'] = 'rcore.products.api.product.products_search'
override_whitelisted_methods['rcore.api.product.products_search'] = 'rcore.products.api.product.products_search'
whitelisted_methods['rcore.api.product.read_product_file'] = 'rcore.products.api.product.read_product_file'
override_whitelisted_methods['rcore.api.product.read_product_file'] = 'rcore.products.api.product.read_product_file'
whitelisted_methods['rcore.api.product_extra.create_extra_group'] = 'rcore.products.api.product_extra.create_extra_group'
override_whitelisted_methods['rcore.api.product_extra.create_extra_group'] = 'rcore.products.api.product_extra.create_extra_group'
whitelisted_methods['rcore.api.product_extra.create_extra_value'] = 'rcore.products.api.product_extra.create_extra_value'
override_whitelisted_methods['rcore.api.product_extra.create_extra_value'] = 'rcore.products.api.product_extra.create_extra_value'
whitelisted_methods['rcore.api.product_extra.delete_extra_group'] = 'rcore.products.api.product_extra.delete_extra_group'
override_whitelisted_methods['rcore.api.product_extra.delete_extra_group'] = 'rcore.products.api.product_extra.delete_extra_group'
whitelisted_methods['rcore.api.product_extra.delete_extra_value'] = 'rcore.products.api.product_extra.delete_extra_value'
override_whitelisted_methods['rcore.api.product_extra.delete_extra_value'] = 'rcore.products.api.product_extra.delete_extra_value'
whitelisted_methods['rcore.api.product_extra.get_extra_groups'] = 'rcore.products.api.product_extra.get_extra_groups'
override_whitelisted_methods['rcore.api.product_extra.get_extra_groups'] = 'rcore.products.api.product_extra.get_extra_groups'
whitelisted_methods['rcore.api.product_extra.get_extra_values'] = 'rcore.products.api.product_extra.get_extra_values'
override_whitelisted_methods['rcore.api.product_extra.get_extra_values'] = 'rcore.products.api.product_extra.get_extra_values'
whitelisted_methods['rcore.api.product_extra.update_extra_group'] = 'rcore.products.api.product_extra.update_extra_group'
override_whitelisted_methods['rcore.api.product_extra.update_extra_group'] = 'rcore.products.api.product_extra.update_extra_group'
whitelisted_methods['rcore.api.product_extra.update_extra_value'] = 'rcore.products.api.product_extra.update_extra_value'
override_whitelisted_methods['rcore.api.product_extra.update_extra_value'] = 'rcore.products.api.product_extra.update_extra_value'
whitelisted_methods['rcore.api.stock.create_stock'] = 'rcore.products.api.stock.create_stock'
override_whitelisted_methods['rcore.api.stock.create_stock'] = 'rcore.products.api.stock.create_stock'
whitelisted_methods['rcore.api.stock.delete_stock'] = 'rcore.products.api.stock.delete_stock'
override_whitelisted_methods['rcore.api.stock.delete_stock'] = 'rcore.products.api.stock.delete_stock'
whitelisted_methods['rcore.api.stock.get_product_stocks'] = 'rcore.products.api.stock.get_product_stocks'
override_whitelisted_methods['rcore.api.stock.get_product_stocks'] = 'rcore.products.api.stock.get_product_stocks'
whitelisted_methods['rcore.api.stock.update_stock'] = 'rcore.products.api.stock.update_stock'
override_whitelisted_methods['rcore.api.stock.update_stock'] = 'rcore.products.api.stock.update_stock'
doc_events = globals().get('doc_events', {})
doc_events.setdefault('Item', {})
_ev = doc_events['Item'].get('on_update') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.products.doctype.product.product.auto_vectorize_product']:
    if _h not in _ev: _ev.append(_h)
doc_events['Item']['on_update'] = _ev
_ev = doc_events['Item'].get('after_insert') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.products.doctype.product.product.auto_vectorize_product']:
    if _h not in _ev: _ev.append(_h)
doc_events['Item']['after_insert'] = _ev
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Brand']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Combo']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Category']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Review']]})

# --- Module: promotions ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('daily', [])
for _t in ['rcore.promotions.tasks.remove_expired_stories']:
    if _t not in scheduler_events['daily']: scheduler_events['daily'].append(_t)
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.banner.get_ad'] = 'rcore.promotions.api.banner.get_ad'
override_whitelisted_methods['rcore.api.banner.get_ad'] = 'rcore.promotions.api.banner.get_ad'
whitelisted_methods['rcore.api.banner.get_ads'] = 'rcore.promotions.api.banner.get_ads'
override_whitelisted_methods['rcore.api.banner.get_ads'] = 'rcore.promotions.api.banner.get_ads'
whitelisted_methods['rcore.api.banner.get_banner'] = 'rcore.promotions.api.banner.get_banner'
override_whitelisted_methods['rcore.api.banner.get_banner'] = 'rcore.promotions.api.banner.get_banner'
whitelisted_methods['rcore.api.banner.get_banners'] = 'rcore.promotions.api.banner.get_banners'
override_whitelisted_methods['rcore.api.banner.get_banners'] = 'rcore.promotions.api.banner.get_banners'
whitelisted_methods['rcore.api.faq.get_faqs'] = 'rcore.base.api.faq.faq.get_faqs'
override_whitelisted_methods['rcore.api.faq.get_faqs'] = 'rcore.base.api.faq.faq.get_faqs'
whitelisted_methods['rcore.api.story.get_story'] = 'rcore.merchants.api.story.story.get_story'
override_whitelisted_methods['rcore.api.story.get_story'] = 'rcore.merchants.api.story.story.get_story'
whitelisted_methods['rcore.api.banner.like_banner'] = 'rcore.promotions.api.banner.like_banner'
override_whitelisted_methods['rcore.api.banner.like_banner'] = 'rcore.promotions.api.banner.like_banner'
whitelisted_methods['rcore.api.ads_package.create_ads_package'] = 'rcore.promotions.api.ads_package.create_ads_package'
override_whitelisted_methods['rcore.api.ads_package.create_ads_package'] = 'rcore.promotions.api.ads_package.create_ads_package'
whitelisted_methods['rcore.api.ads_package.delete_ads_package'] = 'rcore.promotions.api.ads_package.delete_ads_package'
override_whitelisted_methods['rcore.api.ads_package.delete_ads_package'] = 'rcore.promotions.api.ads_package.delete_ads_package'
whitelisted_methods['rcore.api.ads_package.get_ads_packages'] = 'rcore.promotions.api.ads_package.get_ads_packages'
override_whitelisted_methods['rcore.api.ads_package.get_ads_packages'] = 'rcore.promotions.api.ads_package.get_ads_packages'
whitelisted_methods['rcore.api.ads_package.update_ads_package'] = 'rcore.promotions.api.ads_package.update_ads_package'
override_whitelisted_methods['rcore.api.ads_package.update_ads_package'] = 'rcore.promotions.api.ads_package.update_ads_package'
whitelisted_methods['rcore.api.blog.create_admin_blog'] = 'rcore.base.api.blog.blog.create_admin_blog'
override_whitelisted_methods['rcore.api.blog.create_admin_blog'] = 'rcore.base.api.blog.blog.create_admin_blog'
whitelisted_methods['rcore.api.blog.create_blog'] = 'rcore.base.api.blog.blog.create_blog'
override_whitelisted_methods['rcore.api.blog.create_blog'] = 'rcore.base.api.blog.blog.create_blog'
whitelisted_methods['rcore.api.blog.delete_admin_blog'] = 'rcore.base.api.blog.blog.delete_admin_blog'
override_whitelisted_methods['rcore.api.blog.delete_admin_blog'] = 'rcore.base.api.blog.blog.delete_admin_blog'
whitelisted_methods['rcore.api.blog.delete_blog'] = 'rcore.base.api.blog.blog.delete_blog'
override_whitelisted_methods['rcore.api.blog.delete_blog'] = 'rcore.base.api.blog.blog.delete_blog'
whitelisted_methods['rcore.api.blog.get_admin_blogs'] = 'rcore.base.api.blog.blog.get_admin_blogs'
override_whitelisted_methods['rcore.api.blog.get_admin_blogs'] = 'rcore.base.api.blog.blog.get_admin_blogs'
whitelisted_methods['rcore.api.blog.get_blog'] = 'rcore.base.api.blog.blog.get_blog'
override_whitelisted_methods['rcore.api.blog.get_blog'] = 'rcore.base.api.blog.blog.get_blog'
whitelisted_methods['rcore.api.blog.get_blog_details'] = 'rcore.base.api.blog.blog.get_blog_details'
override_whitelisted_methods['rcore.api.blog.get_blog_details'] = 'rcore.base.api.blog.blog.get_blog_details'
whitelisted_methods['rcore.api.blog.get_blogs'] = 'rcore.base.api.blog.blog.get_blogs'
override_whitelisted_methods['rcore.api.blog.get_blogs'] = 'rcore.base.api.blog.blog.get_blogs'
whitelisted_methods['rcore.api.blog.update_admin_blog'] = 'rcore.base.api.blog.blog.update_admin_blog'
override_whitelisted_methods['rcore.api.blog.update_admin_blog'] = 'rcore.base.api.blog.blog.update_admin_blog'
whitelisted_methods['rcore.api.blog.update_blog'] = 'rcore.base.api.blog.blog.update_blog'
override_whitelisted_methods['rcore.api.blog.update_blog'] = 'rcore.base.api.blog.blog.update_blog'
whitelisted_methods['rcore.api.career.get_admin_careers'] = 'rcore.base.api.career.career.get_admin_careers'
override_whitelisted_methods['rcore.api.career.get_admin_careers'] = 'rcore.base.api.career.career.get_admin_careers'
whitelisted_methods['rcore.api.career.get_career'] = 'rcore.base.api.career.career.get_career'
override_whitelisted_methods['rcore.api.career.get_career'] = 'rcore.base.api.career.career.get_career'
whitelisted_methods['rcore.api.career.get_careers'] = 'rcore.base.api.career.career.get_careers'
override_whitelisted_methods['rcore.api.career.get_careers'] = 'rcore.base.api.career.career.get_careers'
whitelisted_methods['rcore.api.coupon.check_coupon'] = 'rcore.promotions.api.coupon.check_coupon'
override_whitelisted_methods['rcore.api.coupon.check_coupon'] = 'rcore.promotions.api.coupon.check_coupon'
whitelisted_methods['rcore.api.faq.create_faq'] = 'rcore.base.api.faq.faq.create_faq'
override_whitelisted_methods['rcore.api.faq.create_faq'] = 'rcore.base.api.faq.faq.create_faq'
whitelisted_methods['rcore.api.faq.delete_faq'] = 'rcore.base.api.faq.faq.delete_faq'
override_whitelisted_methods['rcore.api.faq.delete_faq'] = 'rcore.base.api.faq.faq.delete_faq'
whitelisted_methods['rcore.api.faq.update_faq'] = 'rcore.base.api.faq.faq.update_faq'
override_whitelisted_methods['rcore.api.faq.update_faq'] = 'rcore.base.api.faq.faq.update_faq'
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Story']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Coupon']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Banner']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Ad']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Referral']]})

# --- Module: builder ---
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.builder.get_project_version'] = 'rcore.builder.tasks.get_project_version'
override_whitelisted_methods['rcore.api.builder.get_project_version'] = 'rcore.builder.tasks.get_project_version'
whitelisted_methods['rcore.api.builder.generate_flutter_app'] = 'rcore.builder.tasks.generate_flutter_app'
override_whitelisted_methods['rcore.api.builder.generate_flutter_app'] = 'rcore.builder.tasks.generate_flutter_app'
before_uninstall = globals().get('before_uninstall', [])
if 'rcore.builder.utils.prevent_uninstall_if_build_active' not in before_uninstall: before_uninstall.append('rcore.builder.utils.prevent_uninstall_if_build_active')

# --- Module: crm ---
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('daily_maintenance', [])
for _t in ['rcore.crm.doctype.opportunity.opportunity.auto_close_opportunity', 'rcore.crm.doctype.contract.contract.update_status_for_contracts', 'rcore.crm.doctype.email_campaign.email_campaign.send_email_to_leads_or_contacts', 'rcore.crm.doctype.email_campaign.email_campaign.set_email_campaign_status', 'rcore.crm.utils.open_leads_opportunities_based_on_todays_event']:
    if _t not in scheduler_events['daily_maintenance']: scheduler_events['daily_maintenance'].append(_t)
scheduler_events = globals().get('scheduler_events', {})
scheduler_events.setdefault('hourly_maintenance', [])
for _t in ['rcore.crm.doctype.appointment.appointment.handle_expired_unverified_appointments']:
    if _t not in scheduler_events['hourly_maintenance']: scheduler_events['hourly_maintenance'].append(_t)
override_doctype_class = globals().get('override_doctype_class', {})
override_doctype_class['Contact'] = 'rcore.crm.crm.overrides.contact.CustomContact'
whitelisted_methods = globals().get('whitelisted_methods', {})
override_whitelisted_methods = globals().get('override_whitelisted_methods', {})
whitelisted_methods['rcore.api.crm.doc.get_data'] = 'rcore.crm.crm.doc.doc.get_data'
override_whitelisted_methods['rcore.api.crm.doc.get_data'] = 'rcore.crm.crm.doc.doc.get_data'
whitelisted_methods['rcore.api.crm.doc.sort_options'] = 'rcore.crm.crm.doc.doc.sort_options'
override_whitelisted_methods['rcore.api.crm.doc.sort_options'] = 'rcore.crm.crm.doc.doc.sort_options'
whitelisted_methods['rcore.api.crm.doc.get_filterable_fields'] = 'rcore.crm.crm.doc.doc.get_filterable_fields'
override_whitelisted_methods['rcore.api.crm.doc.get_filterable_fields'] = 'rcore.crm.crm.doc.doc.get_filterable_fields'
whitelisted_methods['rcore.api.crm.doc.get_group_by_fields'] = 'rcore.crm.crm.doc.doc.get_group_by_fields'
override_whitelisted_methods['rcore.api.crm.doc.get_group_by_fields'] = 'rcore.crm.crm.doc.doc.get_group_by_fields'
whitelisted_methods['rcore.api.crm.doc.get_quick_filters'] = 'rcore.crm.crm.doc.doc.get_quick_filters'
override_whitelisted_methods['rcore.api.crm.doc.get_quick_filters'] = 'rcore.crm.crm.doc.doc.get_quick_filters'
whitelisted_methods['rcore.api.crm.doc.get_fields'] = 'rcore.crm.crm.doc.doc.get_fields'
override_whitelisted_methods['rcore.api.crm.doc.get_fields'] = 'rcore.crm.crm.doc.doc.get_fields'
whitelisted_methods['rcore.api.crm.doc.get_assigned_users'] = 'rcore.crm.crm.doc.doc.get_assigned_users'
override_whitelisted_methods['rcore.api.crm.doc.get_assigned_users'] = 'rcore.crm.crm.doc.doc.get_assigned_users'
whitelisted_methods['rcore.api.crm.doc.remove_assignments'] = 'rcore.crm.crm.doc.doc.remove_assignments'
override_whitelisted_methods['rcore.api.crm.doc.remove_assignments'] = 'rcore.crm.crm.doc.doc.remove_assignments'
whitelisted_methods['rcore.api.crm.doc.delete_bulk_docs'] = 'rcore.crm.crm.doc.doc.delete_bulk_docs'
override_whitelisted_methods['rcore.api.crm.doc.delete_bulk_docs'] = 'rcore.crm.crm.doc.doc.delete_bulk_docs'
whitelisted_methods['rcore.api.crm.doc.get_linked_docs_of_document'] = 'rcore.crm.crm.doc.doc.get_linked_docs_of_document'
override_whitelisted_methods['rcore.api.crm.doc.get_linked_docs_of_document'] = 'rcore.crm.crm.doc.doc.get_linked_docs_of_document'
whitelisted_methods['rcore.api.crm.doc.remove_linked_doc_reference'] = 'rcore.crm.crm.doc.doc.remove_linked_doc_reference'
override_whitelisted_methods['rcore.api.crm.doc.remove_linked_doc_reference'] = 'rcore.crm.crm.doc.doc.remove_linked_doc_reference'
whitelisted_methods['rcore.api.crm.contact.get_linked_deals'] = 'rcore.crm.crm.contact.contact.get_linked_deals'
override_whitelisted_methods['rcore.api.crm.contact.get_linked_deals'] = 'rcore.crm.crm.contact.contact.get_linked_deals'
whitelisted_methods['rcore.api.crm.contact.create_new'] = 'rcore.crm.crm.contact.contact.create_new'
override_whitelisted_methods['rcore.api.crm.contact.create_new'] = 'rcore.crm.crm.contact.contact.create_new'
whitelisted_methods['rcore.api.crm.contact.set_as_primary'] = 'rcore.crm.crm.contact.contact.set_as_primary'
override_whitelisted_methods['rcore.api.crm.contact.set_as_primary'] = 'rcore.crm.crm.contact.contact.set_as_primary'
whitelisted_methods['rcore.api.crm.contact.search_emails'] = 'rcore.crm.crm.contact.contact.search_emails'
override_whitelisted_methods['rcore.api.crm.contact.search_emails'] = 'rcore.crm.crm.contact.contact.search_emails'
whitelisted_methods['rcore.api.crm.lead.convert_to_deal'] = 'rcore.crm.doctype.lead.lead.convert_to_deal'
override_whitelisted_methods['rcore.api.crm.lead.convert_to_deal'] = 'rcore.crm.doctype.lead.lead.convert_to_deal'
whitelisted_methods['rcore.api.crm.deal.create_deal'] = 'rcore.crm.doctype.opportunity.opportunity.create_deal'
override_whitelisted_methods['rcore.api.crm.deal.create_deal'] = 'rcore.crm.doctype.opportunity.opportunity.create_deal'
whitelisted_methods['rcore.api.crm.deal.add_contact'] = 'rcore.crm.doctype.opportunity.opportunity.add_contact'
override_whitelisted_methods['rcore.api.crm.deal.add_contact'] = 'rcore.crm.doctype.opportunity.opportunity.add_contact'
whitelisted_methods['rcore.api.crm.deal.remove_contact'] = 'rcore.crm.doctype.opportunity.opportunity.remove_contact'
override_whitelisted_methods['rcore.api.crm.deal.remove_contact'] = 'rcore.crm.doctype.opportunity.opportunity.remove_contact'
whitelisted_methods['rcore.api.crm.deal.set_primary_contact'] = 'rcore.crm.doctype.opportunity.opportunity.set_primary_contact'
override_whitelisted_methods['rcore.api.crm.deal.set_primary_contact'] = 'rcore.crm.doctype.opportunity.opportunity.set_primary_contact'
whitelisted_methods['rcore.api.crm.deal.get_deal_contacts'] = 'rcore.crm.crm.deal.deal.get_deal_contacts'
override_whitelisted_methods['rcore.api.crm.deal.get_deal_contacts'] = 'rcore.crm.crm.deal.deal.get_deal_contacts'
whitelisted_methods['rcore.api.crm.note.get_linked_notes'] = 'rcore.crm.crm.note.note.get_linked_notes'
override_whitelisted_methods['rcore.api.crm.note.get_linked_notes'] = 'rcore.crm.crm.note.note.get_linked_notes'
whitelisted_methods['rcore.api.crm.task.get_linked_tasks'] = 'rcore.crm.crm.task.task.get_linked_tasks'
override_whitelisted_methods['rcore.api.crm.task.get_linked_tasks'] = 'rcore.crm.crm.task.task.get_linked_tasks'
whitelisted_methods['rcore.api.crm.organization.get_organizations'] = 'rcore.crm.crm.organization.organization.get_organizations'
override_whitelisted_methods['rcore.api.crm.organization.get_organizations'] = 'rcore.crm.crm.organization.organization.get_organizations'
whitelisted_methods['rcore.api.crm.call_log.get_call_log'] = 'rcore.crm.crm.call_log.call_log.get_call_log'
override_whitelisted_methods['rcore.api.crm.call_log.get_call_log'] = 'rcore.crm.crm.call_log.call_log.get_call_log'
whitelisted_methods['rcore.api.crm.call_log.create_lead_from_call_log'] = 'rcore.crm.crm.call_log.call_log.create_lead_from_call_log'
override_whitelisted_methods['rcore.api.crm.call_log.create_lead_from_call_log'] = 'rcore.crm.crm.call_log.call_log.create_lead_from_call_log'
whitelisted_methods['rcore.api.crm.products.get_product_rate_details'] = 'rcore.crm.crm.products.products.get_product_rate_details'
override_whitelisted_methods['rcore.api.crm.products.get_product_rate_details'] = 'rcore.crm.crm.products.products.get_product_rate_details'
whitelisted_methods['rcore.api.crm.dashboard.get_dashboard'] = 'rcore.crm.crm.dashboard.dashboard.get_dashboard'
override_whitelisted_methods['rcore.api.crm.dashboard.get_dashboard'] = 'rcore.crm.crm.dashboard.dashboard.get_dashboard'
whitelisted_methods['rcore.api.crm.dashboard.get_chart'] = 'rcore.crm.crm.dashboard.dashboard.get_chart'
override_whitelisted_methods['rcore.api.crm.dashboard.get_chart'] = 'rcore.crm.crm.dashboard.dashboard.get_chart'
whitelisted_methods['rcore.api.crm.dashboard.reset_to_default'] = 'rcore.crm.crm.dashboard.dashboard.reset_to_default'
override_whitelisted_methods['rcore.api.crm.dashboard.reset_to_default'] = 'rcore.crm.crm.dashboard.dashboard.reset_to_default'
doc_events = globals().get('doc_events', {})
doc_events.setdefault('Communication', {})
_ev = doc_events['Communication'].get('after_insert') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.crm.utils.link_communications_with_prospect', 'rcore.crm.utils.update_modified_timestamp']:
    if _h not in _ev: _ev.append(_h)
doc_events['Communication']['after_insert'] = _ev
doc_events.setdefault('Contact', {})
_ev = doc_events['Contact'].get('validate') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.crm.crm.contact.contact.validate', 'rcore.crm.utils.update_lead_phone_numbers']:
    if _h not in _ev: _ev.append(_h)
doc_events['Contact']['validate'] = _ev
doc_events.setdefault('Contact Us Settings', {})
_ev = doc_events['Contact Us Settings'].get('on_update') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.crm.utils.disable_opportunity_creation_on_contact_us_disabled']:
    if _h not in _ev: _ev.append(_h)
doc_events['Contact Us Settings']['on_update'] = _ev
doc_events.setdefault('Email Unsubscribe', {})
_ev = doc_events['Email Unsubscribe'].get('after_insert') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.crm.doctype.email_campaign.email_campaign.unsubscribe_recipient']:
    if _h not in _ev: _ev.append(_h)
doc_events['Email Unsubscribe']['after_insert'] = _ev
doc_events.setdefault('Event', {})
_ev = doc_events['Event'].get('after_insert') or []
_ev = [_ev] if isinstance(_ev, str) else list(_ev)
for _h in ['rcore.crm.utils.link_events_with_prospect']:
    if _h not in _ev: _ev.append(_h)
doc_events['Event']['after_insert'] = _ev
fixtures = globals().get('fixtures', [])
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Appointment']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Appointment Booking Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Appointment Booking Slots']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Availability Of Slots']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Campaign']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Campaign Email Schedule']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Communication Status']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Competitor']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Competitor Customer Win']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Competitor Detail']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Competitor Location']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Competitor Opportunity']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Competitor Product']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Competitor Route']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Competitor Team Intel']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Competitor Zone']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Contract']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Contract Fulfilment Checklist']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Contract Template']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Contract Template Fulfilment Terms']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'CRM Note']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'CRM Settings']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Deal Status']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Email Campaign']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Lead']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Lead Source']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Lead Status']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Lost Reason Detail']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Market Segment']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Opportunity']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Opportunity Contact']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Opportunity Item']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Opportunity Lost Reason']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Opportunity Lost Reason Detail']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Opportunity Type']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Prospect']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Prospect Lead']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Prospect Opportunity']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Sales Dashboard']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Sales Note']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Sales Stage']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Sales Task']]})
fixtures.append({'dt': 'DocType', 'filters': [['name', '=', 'Status Change Log']]})
# --- END OF DYNAMIC SDK HOOKS ---
