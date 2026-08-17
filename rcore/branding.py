from typing import Any, Optional
# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_paas_branding():
    """Get PaaS branding settings for tenant"""
    try:
        # Check if tenant has PaaS plan
        subscription = frappe.db.get_value('Company Subscription',
                                           {'company': frappe.defaults.get_user_default(
                                               'Company')},
                                           ['subscription_plan'], as_dict=True)

        if not subscription:
            return {'enabled': False}

        # Check if plan includes PaaS
        plan = frappe.get_doc(
            'Subscription Plan',
            subscription.subscription_plan)
        has_paas = any(module.module_name == 'PaaS' for module in plan.modules)

        if not has_paas:
            return {'enabled': False}

        # Get PaaS settings logo and app name
        settings = frappe.get_single('Settings')

        # Use Settings logo if available, otherwise fallback to ROKCT default
        # logos
        logo = settings.logo if settings and settings.logo else '/assets/rokct/images/logo.svg'
        favicon = settings.favicon if settings and settings.favicon else '/assets/rokct/images/logo.svg'
        app_name = settings.project_title if settings and settings.project_title else 'ROKCT'

        return {
            'enabled': True,
            'logo': logo,
            'app_name': app_name,
            'favicon': favicon,
            'logo_dark': '/assets/rokct/images/logo_dark.svg'  # Dark mode logo
        }

    except Exception as e:
        frappe.log_error(f"PaaS branding error: {str(e)}")
        return {'enabled': False}


def get_paas_brand_html():
    """Generate PaaS branding HTML/CSS"""
    branding = get_paas_branding()

    if not branding.get('enabled'):
        return ""

    logo_url = branding.get('logo', '')
    app_name = branding.get('app_name', 'My App')

    # Logo replacement script
    logo_script = f"""
    <script>
        frappe.ready(function() {{
            // Replace all Frappe and ERPNext logos with PaaS logo
            setTimeout(function() {{
                // Navbar logo
                $('.navbar-brand img, .app-logo img, .navbar-home img').attr('src', '{logo_url}');

                // Login page logo
                $('.login-content img, .for-login img').attr('src', '{logo_url}');

                // Sidebar logo
                $('.sidebar-logo img').attr('src', '{logo_url}');

                // All Frappe/ERPNext logos
                $('img').each(function() {{
                    var src = $(this).attr('src');
                    if (src && (src.includes('frappe') || src.includes('erpnext') || src.includes('logo'))) {{
                        $(this).attr('src', '{logo_url}');
                    }}
                }});

                // Set favicon
                $('link[rel="icon"]').attr('href', '{logo_url}');
                $('link[rel="shortcut icon"]').attr('href', '{logo_url}');

                // Update page title
                document.title = '{app_name}';
            }}, 500);

            // Re-apply on page navigation
            frappe.router.on('change', function() {{
                setTimeout(function() {{
                    $('.navbar-brand img, .app-logo img').attr('src', '{logo_url}');
                }}, 300);
            }});
        }});
    </script>

    <style>
        /* Hide Frappe/ERPNext branding */
        .powered-by-frappe,
        .footer-powered,
        [class*="powered-by"] {{
            display: none !important;
        }}
    </style>
    """

    return logo_script


@frappe.whitelist(allow_guest=True)
def get_paas_branding_for_tenant() -> Any:
    """API endpoint to get PaaS branding"""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    branding = get_paas_branding()
    return branding
