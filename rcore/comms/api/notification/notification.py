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
import json
import requests
from rcore.base.api.utils import api_response


@frappe.whitelist()
def send_push_notification(user: str, title: str, body: str, data: dict=None) -> Any:
    """
    Sends a push notification to a specific user via FCM.
    """
    try:
        settings = frappe.get_single("Push Notification Settings")
        if not settings.server_key:
            frappe.log_error(
                "FCM Server Key is missing in Push Notification Settings",
                "Push Notification Error",
            )
            return {"status": "failed", "message": "Server key missing."}

        tokens = frappe.get_all(
            "Device Token", filters={"user": user}, pluck="device_token"
        )
        if not tokens:
            return {
                "status": "failed",
                "message": "No device tokens found for user.",
            }

        headers = {
            "Authorization": f"key={settings.server_key}",
            "Content-Type": "application/json",
        }

        success_count = 0
        failure_count = 0

        for token in tokens:
            payload = {
                "to": token,
                "notification": {"title": title, "body": body},
                "data": data or {},
            }

            try:
                response = requests.post(
                    "https://fcm.googleapis.com/fcm/send",
                    headers=headers,
                    json=payload,
                    timeout=5,
                )
                if response.status_code == 200:
                    success_count += 1
                else:
                    failure_count += 1
                    frappe.log_error(f"FCM Error for {token}: {
                        response.text}", "Push Notification Error")
            except Exception as e:
                failure_count += 1
                frappe.log_error(f"Request Error for {token}: {
                    str(e)}", "Push Notification Error")

        return {
            "status": "success",
            "message": f"Sent: {success_count}, Failed: {failure_count}",
            "details": {"sent": success_count, "failed": failure_count},
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Push Notification Exception")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def get_default_sms_payload() -> Any:
    """
    Returns the default SMS payload from Push Notification Settings.
    """
    settings = frappe.get_single("Push Notification Settings")

    payload = {
        "default": True,
        "api_key": settings.api_key,
        "ios_api_key": settings.ios_api_key,
        "android_api_key": settings.android_api_key,
        "server_key": settings.server_key,
        "vapid_key": settings.vapid_key,
        "auth_domain": settings.auth_domain,
        "project_id": settings.project_id,
        "storage_bucket": settings.storage_bucket,
        "message_sender_id": settings.messaging_sender_id,
        "app_id": settings.app_id,
        "measurement_id": settings.measurement_id,
    }

    return json.dumps(payload)


@frappe.whitelist()
def get_notification_settings() -> Any:
    """
    Retrieves notification settings for the current user.
    Returns a list of notification types with their active status.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view notification settings.",
            frappe.AuthenticationError,
        )

    # Get all notification types
    # Assuming 'Notification Type' doctype exists from confirmed check
    # If it doesn't exist in some envs, we handle gracefully
    try:
        types = frappe.get_all(
            "Notification Type", fields=["name", "type", "payload"]
        )
    except Exception:
        return api_response(data=[])

    # Get user preferences
    prefs = frappe.get_all(
        "User Notification Preference",
        filters={"user": user},
        fields=["name", "notification_type", "active"],
    )

    prefs_map = {p.notification_type: p for p in prefs}

    result = []
    for t in types:
        # Default to active if no preference set
        is_active = True
        pref_id = None  # noqa: F841

        if t.name in prefs_map:
            is_active = bool(prefs_map[t.name].active)
            _pref_id = prefs_map[t.name].name  # noqa: F841

        result.append(
            {
                # Flutter expects int, send 0 or valid int if available (Doctype
                # doesn't have int id by default)
                "id": 0,
                "type": t.type
                or t.name,  # Use 'type' field or fallback to name
                "active": is_active,
                "created_at": None,
                "updated_at": None,
                "payload": (
                    json.loads(t.payload)
                    if t.payload and isinstance(t.payload, str)
                    else (t.payload or [])
                ),
            }
        )

    # Wrap in data.data as per Flutter model
    return api_response(data={"data": result})


@frappe.whitelist()
def update_notification_settings(type: str, active: int) -> Any:
    """
    Updates the notification setting for a specific type.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update notification settings.",
            frappe.AuthenticationError,
        )

    # Check if preference exists
    # We match by 'notification_type' which is the Link to Notification Type
    # But input 'type' might be the string 'Order Update' etc from the 'type' field of Notification Type doctype
    # We need to resolve it to the Notification Type name

    nt_name = frappe.db.get_value("Notification Type", {"type": type}, "name")
    if not nt_name:
        # fallback if type passed IS the name
        if frappe.db.exists("Notification Type", type):
            nt_name = type
        else:
            frappe.throw(f"Invalid notification type: {type}")

    # Find existing preference
    pref_name = frappe.db.get_value(
        "User Notification Preference",
        {"user": user, "notification_type": nt_name},
        "name",
    )

    if pref_name:
        doc = frappe.get_doc("User Notification Preference", pref_name)
        doc.active = 1 if active else 0
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc(
            {
                "doctype": "User Notification Preference",
                "user": user,
                "notification_type": nt_name,
                "active": 1 if active else 0,
            }
        ).insert(ignore_permissions=True)

    return api_response(message="Notification settings updated successfully.")


@frappe.whitelist()
def get_user_notifications(start: Any=0, limit: Any=20) -> Any:
    """
    Retrieves the list of notifications for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your notifications.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "Notification Log",
        filters={"user": user},
        fields=[
            "name",
            "subject",
            "document_type",
            "document_name",
            "creation",
            "read",
        ],
        order_by="creation desc",
        offset=start,
        limit=limit,
    )


@frappe.whitelist()
def get_notification_count() -> Any:
    """
    Retrieves the count of unread notifications for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        return api_response(data={"count": 0})

    count = frappe.db.count("Notification Log", {"user": user, "read": 0})
    return api_response(data={"count": count})


@frappe.whitelist()
def mark_notification_logs_as_read(ids: Any=None) -> Any:
    """
    Marks specific notification logs as read.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in.", frappe.AuthenticationError)

    if isinstance(ids, str):
        ids = json.loads(ids)

    if not ids:
        return api_response(message="No IDs provided")

    for name in ids:
        if frappe.db.exists("Notification Log", name):
            doc = frappe.get_doc("Notification Log", name)
            # Check ownership/for_user
            if (
                hasattr(doc, "for_user") and doc.for_user == user
            ) or doc.owner == user:
                doc.read = 1
                doc.save(ignore_permissions=True)

    return api_response(message="Notifications marked as read")


@frappe.whitelist()
def read_all_notifications() -> Any:
    """
    Marks all notifications as read for the current user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in.", frappe.AuthenticationError)

    logs = frappe.get_all(
        "Notification Log", filters={"for_user": user, "read": 0}
    )
    # Also check owner if for_user is not used? Standard Frappe uses for_user
    for log in logs:
        frappe.db.set_value("Notification Log", log.name, "read", 1)

    return api_response(message="All notifications marked as read")


@frappe.whitelist()
def read_one_notification(name: Any) -> Any:
    """
    Marks a single notification as read.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in.", frappe.AuthenticationError)

    if frappe.db.exists("Notification Log", name):
        doc = frappe.get_doc("Notification Log", name)
        if (
            hasattr(doc, "for_user") and doc.for_user == user
        ) or doc.owner == user:
            doc.read = 1
            doc.save(ignore_permissions=True)

    return api_response(message="Notification marked as read")
