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
import hmac
import random
import json
import uuid
import csv
import io
from frappe.rate_limiter import rate_limit
from rcore.core.utils import check_subscription_feature
from rcore.api.utils import api_response
from rcore.api.idempotency import idempotent


@frappe.whitelist()
def logout() -> Any:
    """
    Log out the current user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    frappe.local.login_manager.logout()
    return api_response(message="User successfully logout")


@frappe.whitelist(allow_guest=True)
def login(usr: Any, pwd: Any) -> Any:
    """
    Unified login resolving email or phone to Frappe User document,
    generating api_key, api_secret, refresh_token and expiry.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    from frappe.utils import now_datetime, add_to_date

    # 1. Resolve phone number or email to username
    if usr and (usr.startswith("+") or usr.isdigit()):
        phone_user = frappe.db.get_value("User", {"phone": usr}, "name")
        if phone_user:
            usr = phone_user
    elif usr and "@" in usr:
        email_user = frappe.db.get_value("User", {"email": usr}, "name")
        if email_user:
            usr = email_user

    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
    except frappe.AuthenticationError:
        return api_response(message="Invalid credentials", status_code=401)

    user = frappe.get_doc("User", frappe.session.user)

    # Deferred-OTP limit: an account created through register_user (online,
    # or an offline registration replayed later by the app's sync engine)
    # carries email_verification_token until its OTP completes. Such an
    # account must stay limited — offline-synced accounts arrive with a
    # client-generated initial password that cannot be treated as proof of
    # identity, so no session token is issued until verify_email_code /
    # verify_phone_code has set a *_verified_at timestamp (those endpoints
    # mint the first real token themselves). Accounts created outside
    # register_user (setup wizard, admin, Google login) never carry the
    # token and are unaffected.
    if (
        not getattr(user, "email_verified_at", None)
        and not getattr(user, "phone_verified_at", None)
        and getattr(user, "email_verification_token", None)
    ):
        login_manager.logout()
        return api_response(
            message="Account not verified. Complete the OTP verification "
            "sent to your email or phone to activate this account.",
            status_code=403,
            data={
                "verification_required": True,
                "email": user.email,
                "phone": getattr(user, "phone", None),
            },
        )

    # 2. Generate new API Keys & Expiry details
    api_secret = frappe.generate_hash(length=15)
    api_key = frappe.generate_hash(length=15)
    refresh_token = frappe.generate_hash(length=32)
    expiry_date = add_to_date(now_datetime(), hours=24)

    frappe.db.set_value(
        "User",
        user.name,
        {
            "api_key": api_key,
            "api_secret": api_secret,
            "custom_refresh_token": refresh_token,
            "custom_token_expiry": expiry_date
        },
        update_modified=False,
    )

    # 3. Determine User Roles for primary role logic
    user_roles = frappe.get_roles(user.name)
    primary_role = "user"
    if "Administrator" in user_roles:
        primary_role = "Administrator"
    elif "System Manager" in user_roles:
        primary_role = "System Manager"
    elif user.user_type == "System User":
        primary_role = "System Manager"

    token = f"{api_key}:{api_secret}"

    # 4. Fetch shop details if available
    shop = None
    try:
        shop_name = frappe.db.get_value("Shop", {"user": user.name}, "name")
        if shop_name:
            shop_doc = frappe.get_doc("Shop", shop_name)
            shop = {
                "id": shop_doc.name,
                "uuid": shop_doc.uuid,
                "name": shop_doc.shop_name,
                "logo": shop_doc.logo,
                "cover_photo": shop_doc.cover_photo,
                "active": shop_doc.open,
                "status": shop_doc.status,
            }
    except Exception:
        pass

    return api_response(
        message="Logged In",
        data={
            "access_token": token,
            "refresh_token": refresh_token,
            "expires_at": expiry_date,
            "token_type": "Bearer",
            "user": {
                "id": user.name,
                "email": user.email,
                "firstname": user.first_name,
                "lastname": user.last_name,
                "phone": getattr(user, "phone", None) or getattr(user, "mobile_no", None),
                "role": primary_role,
                "active": 1,
                "img": user.user_image,
                "shop": shop,
                "home_page": user.get_home_page(),
            },
        },
    )


@frappe.whitelist()
def get_profile() -> Any:
    """
    The get_profile function retrieves the current user's profile details. It does not accept any parameters. This function first checks if the user is logged in, throwing an AuthenticationError if they are not. It then fetches the user's details from the database and, if applicable, their associated shop details. The function returns a response containing the user's profile information, including their ID, email, name, phone number, role, and image, as well as their shop details and wallet balance.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Get the current user's profile details.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your profile.",
            frappe.AuthenticationError,
        )

    user_doc = frappe.get_doc("User", user)

    # Fetch shop details if available
    shop = None
    shop_name = frappe.db.get_value("Shop", {"user": user}, "name")
    if shop_name:
        try:
            shop_doc = frappe.get_doc("Shop", shop_name)
            shop = {
                "id": shop_doc.name,
                "uuid": shop_doc.uuid,
                "name": shop_doc.shop_name,
                "logo": shop_doc.logo,
                "cover_photo": shop_doc.cover_photo,
                "active": shop_doc.open,
                "status": shop_doc.status,
            }
        except Exception:
            pass

    return api_response(
        data={
            "id": user_doc.name,
            "email": user_doc.email,
            "firstname": user_doc.first_name,
            "lastname": user_doc.last_name,
            "phone": user_doc.phone,
            "role": "user",
            "active": 1,
            "img": user_doc.user_image,
            "shop": shop,
            "wallet": frappe.db.get_value(
                "Wallet", {"user": user_doc.name}, "balance"
            )
            or 0.0,
        }
    )


@frappe.whitelist()
def update_profile(firstname: Any=None, lastname: Any=None, email: Any=None, phone: Any=None, images: Any=None) -> Any:
    """
    The update_profile function updates the current user's profile information. It accepts several optional parameters: firstname, lastname, email, phone, and images, which correspond to the user's first name, last name, email address, phone number, and profile image, respectively. If any of these parameters are provided, the function will update the corresponding field in the user's profile. The function requires the user to be logged in and will throw an error if the user is a guest. The email parameter is currently not utilized in the function. The function returns the updated profile information.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Update the current user's profile.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your profile.",
            frappe.AuthenticationError,
        )

    user_doc = frappe.get_doc("User", user)

    if firstname:
        user_doc.first_name = firstname
    if lastname:
        user_doc.last_name = lastname
    if phone:
        user_doc.phone = phone

    # Handle Image Upload (expects list or single string URL)
    if images:
        if isinstance(images, list) and len(images) > 0:
            user_doc.user_image = images[0]
        elif isinstance(images, str):
            user_doc.user_image = images

    user_doc.save(ignore_permissions=True)
    return get_profile()


@frappe.whitelist()
def update_password(password: Any, password_confirmation: Any) -> Any:
    """
    The update_password function is used to update the current user's password. It takes two parameters: password and password_confirmation. The password parameter is the new password to be set, while the password_confirmation parameter is used to verify that the new password was entered correctly. The function checks if the user is logged in and if the password and confirmation match, then updates the user's password and returns a success message.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Update the current user's password.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your password.",
            frappe.AuthenticationError,
        )

    if password != password_confirmation:
        frappe.throw("Password confirmation does not match.")

    user_doc = frappe.get_doc("User", user)
    user_doc.new_password = password
    user_doc.save(ignore_permissions=True)

    return api_response(message="Password updated successfully")


@frappe.whitelist()
def delete_account() -> Any:
    """
    The delete_account function is used to delete the currently logged-in user's account. If the account cannot be deleted due to linked documents, it will be deactivated instead. This function does not take any parameters, as it relies on the currently logged-in user's information. It first checks if the user is logged in, throwing an AuthenticationError if they are not. The function then attempts to delete the user's account, logging them out and returning a success message if successful. If deletion fails due to linked documents, it deactivates the account, logs the user out, and returns a message indicating that the account has been deactivated.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Deletes the currently logged-in user's account.
    If deletion fails due to linked documents, the account is deactivated instead.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to delete your account.",
            frappe.AuthenticationError,
        )

    try:
        # Attempt to delete the User document
        frappe.delete_doc("User", user, ignore_permissions=True)
        # Logout the session
        if hasattr(frappe.local, "login_manager"):
            frappe.local.login_manager.logout()
        return api_response(message="Account deleted successfully.")
    except (frappe.LinkExistsError, frappe.exceptions.LinkExistsError):
        # Fallback: Deactivate the user if linked documents exist
        frappe.db.set_value("User", user, "enabled", 0)
        if hasattr(frappe.local, "login_manager"):
            frappe.local.login_manager.logout()
        return api_response(message="Account deactivated successfully.")


@frappe.whitelist()
@check_subscription_feature("phone_verification")
def check_phone(phone: str) -> Any:
    """
    The check_phone function checks if a given phone number is already registered to a user. It takes one parameter, phone, which is a string representing the phone number to be checked. The function returns an API response indicating whether the phone number is available or already exists, along with a status of success or error. If the phone parameter is empty, it throws an error as the phone number is a required parameter.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Check if a phone number is already registered to a user.
    """
    if not phone:
        frappe.throw("Phone number is a required parameter.")

    if frappe.db.exists("User", {"phone": phone}):
        return api_response(
            message="Phone number already exists.", data={"status": "error"}
        )
    else:
        return api_response(
            message="Phone number is available.", data={"status": "success"}
        )


# allow_guest: the app requests this OTP unauthenticated — both during
# online phone registration (before any session exists) and for the
# deferred-OTP flow, where an offline-registered account was synced by
# the sync engine and holds no backend session until OTP completes.
# Rate limited per phone number to keep guest access from becoming an
# SMS-bombing vector.
@frappe.whitelist(allow_guest=True)
@rate_limit(key="phone", limit=5, seconds=15 * 60)
@check_subscription_feature("phone_verification")
def send_phone_verification_code(phone: str) -> Any:
    """
    Generate and send a phone verification code (OTP).
    This is used for both initial verification and resending.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not phone:
        frappe.throw("Phone number is a required parameter.")

    # Generate a 6-digit OTP
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])

    # Store the OTP in cache for 10 minutes (600 seconds)
    cache_key = f"phone_otp:{phone}"
    frappe.cache.set_value(cache_key, otp, expires_in_sec=600)

    # Send SMS
    try:
        frappe.send_sms(
            receivers=[phone], message=f"Your verification code is: {otp}"
        )
    except Exception as e:
        frappe.log_error(
            f"Failed to send OTP SMS to {phone}: {e}", "SMS Sending Error"
        )
        frappe.throw(
            "Failed to send verification code. Please try again later."
        )

    return api_response(message="Verification code sent successfully.")


# allow_guest: this is the verify half of the guest OTP pair above, and the
# endpoint that mints the FIRST real session token for a deferred
# (offline-registered, background-synced) account — see the login gate in
# login(). Rate limited per phone so the 6-digit space cannot be brute
# forced within the OTP's 10-minute lifetime.
@frappe.whitelist(allow_guest=True)
@rate_limit(key="phone", limit=10, seconds=15 * 60)
@check_subscription_feature("phone_verification")
def verify_phone_code(phone: str, otp: str) -> Any:
    """
    verify_phone_code(phone: str, otp: str) validates the one‑time password (OTP) that was sent to a user's phone number. It ensures both arguments are provided, retrieves the expected OTP from the cache, and compares it with the supplied value. If the OTP matches, the function locates the corresponding User record, marks the phone as verified, clears the cached OTP, generates new API credentials for the session, and returns a success response containing a token and the user's profile information. If the OTP is missing, expired, incorrect, or the user cannot be found, an appropriate error response is returned.
    
    Parameters  
    - **phone** – The user's phone number as a string; used as the lookup key for the cached OTP and the User document.  
    - **otp** – The OTP string that the user received on their phone and must be verified.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Verify the OTP sent to a user's phone.
    Note: This flow is designed for existing users verifying their number.
    For new user registration, the OTP should be verified before the User doc is created.
    """
    if not phone or not otp:
        frappe.throw("Phone number and OTP are required parameters.")

    cache_key = f"phone_otp:{phone}"
    cached_otp = frappe.cache.get_value(cache_key)

    if not cached_otp:
        return api_response(
            message="OTP expired or was not sent. Please request a new one.",
            status_code=400,
        )

    # encode: compare_digest rejects non-ASCII str, and the otp arrives
    # attacker-controlled.
    if not hmac.compare_digest(str(cached_otp).encode(), str(otp).encode()):
        return api_response(
            message="Invalid verification code.", status_code=400
        )

    # OTP is correct, find user and mark as verified
    try:
        user = frappe.get_doc("User", {"phone": phone})
        if not user.enabled:
            return api_response(
                message="This account is disabled.", status_code=403
            )
        user.phone_verified_at = frappe.utils.now_datetime()
        # The registration OTP parked in email_verification_token is spent
        # now: clearing it closes the stale-token path through
        # verify_my_email and fully lifts the login() deferred-OTP gate.
        user.email_verification_token = None
        user.save(ignore_permissions=True)
    except frappe.DoesNotExistError:
        return api_response(
            message="User with this phone number not found.", status_code=404
        )
    except Exception as e:
        frappe.log_error(
            f"Failed to update phone_verified_at for user with phone {phone}: {e}",
            "Phone Verification Error",
        )
        frappe.throw(
            "An error occurred while verifying your phone number. Please try again."
        )

    # Clear the OTP from cache
    frappe.cache.delete_value(cache_key)

    # Generate fresh API keys for the new session
    api_secret = frappe.generate_hash(length=15)
    user.api_key = frappe.generate_hash(length=15)
    user.api_secret = api_secret
    user.save(ignore_permissions=True)
    frappe.db.commit()

    # Get full profile data matching VerifyData/ProfileData structure
    user_info = {
        "id": user.name,
        "email": user.email,
        "firstname": user.first_name,
        "lastname": user.last_name,
        "phone": user.phone,
        "img": user.user_image,
    }

    return api_response(
        message="Phone number verified successfully.",
        data={"token": f"{user.api_key}:{api_secret}", "user": user_info},
    )


# Rate limited per email: guest-callable with a 6-digit code, so cap
# guesses well below the code space within its 10-minute lifetime.
@frappe.whitelist(allow_guest=True)
@rate_limit(key="email", limit=10, seconds=15 * 60)
def verify_email_code(email: str, otp: str) -> Any:
    """
    The verify_email_code function is used to verify a user's email address using a 6-digit One-Time Password (OTP). It takes two parameters: email and otp, which represent the user's email address and the OTP to be verified, respectively. The function checks if the provided OTP matches the one stored in the cache for the given email address, and if they match, it marks the user as verified, generates new API keys, and returns a successful response with the user's profile data and authentication token. If the OTP is invalid or has expired, or if any other error occurs during the verification process, the function returns an error response with a corresponding status code.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Verify a user's email address using a 6-digit OTP.
    """
    if not email or not otp:
        return api_response(
            message="Email and OTP are required.", status_code=400
        )

    # Retrieve the OTP from cache
    cache_key = f"email_otp:{email}"
    stored_otp = frappe.cache.get_value(cache_key)

    # encode: compare_digest rejects non-ASCII str, and the otp arrives
    # attacker-controlled.
    if not stored_otp or not hmac.compare_digest(
        str(stored_otp).encode(), str(otp).encode()
    ):
        return api_response(
            message="Invalid or expired verification code.", status_code=401
        )

    # Mark the user as verified
    try:
        user = frappe.get_doc("User", email)
        if not user.enabled:
            return api_response(
                message="This account is disabled.", status_code=403
            )
        user.email_verified_at = frappe.utils.now_datetime()
        # Spend the registration OTP parked in email_verification_token —
        # same reasoning as verify_phone_code.
        user.email_verification_token = None
        user.save(ignore_permissions=True)
        frappe.db.commit()

        # Generate fresh API keys for the new session
        api_secret = frappe.generate_hash(length=15)
        user.api_key = frappe.generate_hash(length=15)
        user.api_secret = api_secret
        user.save(ignore_permissions=True)
        frappe.db.commit()

        # Clear the OTP from cache
        frappe.cache.delete_value(cache_key)

        # Get full profile data matching VerifyData/ProfileData structure
        user_info = {
            "id": user.name,
            "email": user.email,
            "firstname": user.first_name,
            "lastname": user.last_name,
            "phone": user.phone,
            "img": user.user_image,
        }

        return api_response(
            message="Email verified successfully.",
            data={"token": f"{user.api_key}:{api_secret}", "user": user_info},
        )
    except frappe.DoesNotExistError:
        return api_response(message="User not found.", status_code=404)
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Email Verification Error")
        return api_response(message=f"An error occurred: {str(e)}", status_code=500)


@frappe.whitelist(allow_guest=True)
@idempotent
def register_user(password: Any, first_name: Any, last_name: Any, email: Any=None, phone: Any=None) -> Any:
    """
    The register_user function is used to create a new user account and send a verification code to the user's email or phone. It takes in several parameters: password, first_name, last_name, email, and phone. The email parameter is optional and defaults to None, while the phone parameter is also optional and defaults to None. If the email is not provided but a phone number is, the function will generate an email address in the format of phone_number@site_prefix.app. The function checks if the email address is already registered and returns an error if it is. It then creates a new user account, generates a 6-digit verification code, and sends it to the user's email or phone. The function returns a response with a message and the user's details.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Register a new user and send a verification code (OTP).
    Handles both email and phone registration.
    """
    # If email is missing but phone exists, use phone as the primary identifier
    if not email and phone:
        # Get the current site name prefix (e.g., 'spazafy' from
        # 'spazafy.tenant.rokct.ai')
        site_prefix = frappe.local.site.split(".")[0]
        email = f"{phone.strip('+')}@{site_prefix}.app"

    if not email:
        return api_response(
            message="Email or Phone is required.", status_code=400
        )

    if frappe.db.exists("User", email):
        return api_response(
            message="Email address already registered.", status_code=409
        )

    # Create the new user
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "send_welcome_email": 0,
            "roles": [{"role": "PaaS User"}, {"role": "user"}],
        }
    )
    user.set("new_password", password)

    # Generate a 6-digit OTP
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])

    # Store the OTP in cache for 10 minutes (600 seconds)
    # We use both email and phone in the key for redundancy
    cache_key = f"email_otp:{email}"
    frappe.cache.set_value(cache_key, otp, expires_in_sec=600)
    if phone:
        frappe.cache.set_value(f"phone_otp:{phone}", otp, expires_in_sec=600)

    # Store token in user doc for verification fallback/tests
    user.email_verification_token = otp
    user.insert(ignore_permissions=True)

    # Deliver OTP based on registration type. Phone registrations carry the
    # synthesized {phone}@{site_prefix}.app address built above — match on
    # THIS site's prefix, not a hardcoded tenant name, so phone-registered
    # accounts (including offline registrations replayed by the sync
    # engine) get their OTP by SMS on every tenant.
    site_prefix = frappe.local.site.split(".")[0]
    is_phone_reg = email.endswith(f"@{site_prefix}.app")
    if is_phone_reg and phone:
        try:
            frappe.send_sms(
                receivers=[phone], message=f"Your verification code is: {otp}"
            )
        except Exception as e:
            frappe.log_error(f"SMS Send Error: {e}")
    else:
        # Send the verification email with the OTP
        email_context = {"first_name": user.first_name, "otp_code": otp}
        frappe.sendmail(
            recipients=[user.email],
            subject="Your Verification Code",
            template="New User Welcome",
            args=email_context,
            now=True,
        )

    return api_response(
        message="User registered successfully. Please check your "
        + ("phone" if is_phone_reg else "email")
        + " for the 6-digit verification code.",
        data={
            "user": {
                # id lets the app's offline sync engine map its local
                # temp id to the backend account (no token is returned —
                # the first session token is minted at OTP verification).
                "id": user.name,
                "email": user.email if not is_phone_reg else None,
                "firstname": user.first_name,
                "lastname": user.last_name,
                "phone": user.phone,
            }
        },
    )


# allow_guest: the deferred-OTP email flow (an offline-registered account
# synced by the app's sync engine) holds no backend session until OTP
# completes, so its resend request arrives unauthenticated. Scope is
# strictly the still-unverified register_user state: accounts that are
# already verified, disabled, or were created outside register_user (no
# email_verification_token) are silently skipped, and the response is the
# same either way so the endpoint cannot be used to enumerate accounts.
@frappe.whitelist(allow_guest=True)
@rate_limit(key="email", limit=5, seconds=60 * 60)
def resend_verification_email(email: str) -> Any:
    """
    Re-send the 6-digit registration verification code for a pending
    (register_user-created, not yet OTP-verified) account.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not email:
        return api_response(message="Email is required.", status_code=400)

    generic = api_response(
        message="If an unverified account exists for this email, a new "
        "verification code has been sent."
    )

    user_name = frappe.db.get_value("User", {"email": email}, "name")
    if not user_name:
        return generic

    user = frappe.get_doc("User", user_name)
    is_pending_registration = (
        user.enabled
        and getattr(user, "email_verification_token", None)
        and not getattr(user, "email_verified_at", None)
        and not getattr(user, "phone_verified_at", None)
    )
    if not is_pending_registration:
        return generic

    # Same OTP conventions as register_user: 6 digits, 10-minute cache,
    # mirrored into email_verification_token for the fallback verify path.
    otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
    frappe.cache.set_value(f"email_otp:{email}", otp, expires_in_sec=600)
    if user.phone:
        frappe.cache.set_value(f"phone_otp:{user.phone}", otp, expires_in_sec=600)
    frappe.db.set_value(
        "User", user_name, "email_verification_token", otp,
        update_modified=False,
    )

    try:
        frappe.sendmail(
            recipients=[user.email],
            subject="Your Verification Code",
            template="New User Welcome",
            args={"first_name": user.first_name, "otp_code": otp},
            now=True,
        )
    except Exception as e:
        frappe.log_error(
            f"Failed to resend verification code to {email}: {e}",
            "Resend Verification Code Error",
        )

    return generic


@frappe.whitelist(allow_guest=True)
def forgot_password(user: str) -> Any:
    """
    The forgot_password function initiates a password reset for a given user, handling both email and phone number inputs. It takes one parameter, user, which is a string representing the user's email address or phone number. The function generates a 6-digit one-time password (OTP) and stores it in the cache with a 10-minute expiration time. If the input is a phone number, it sends the OTP via SMS; otherwise, it sends the OTP via email to the user's registered email address. The function returns a success message, regardless of whether the user exists or not, for security purposes.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Initiate a password reset for a given user.
    Handles both email and phone number inputs.
    """
    try:
        is_phone = user.startswith("+") or user.isdigit()
        # Generate and store 6-digit OTP
        otp = "".join([str(random.randint(0, 9)) for _ in range(6)])
        frappe.cache.set_value(
            f"password_reset_otp:{user}", otp, expires_in_sec=600
        )

        if is_phone:
            try:
                frappe.send_sms(
                    receivers=[user],
                    message=f"Your password reset code is: {otp}",
                )
            except Exception as sms_error:
                frappe.log_error(
                    f"Failed to send password reset SMS to {user}: {sms_error}",
                    "SMS Reset Error",
                )
        else:
            # Send the OTP via email
            user_doc_name = frappe.db.get_value(
                "User", {"email": user}, "name"
            )
            if user_doc_name:
                user_doc = frappe.get_doc("User", user_doc_name)
                frappe.sendmail(
                    recipients=[user],
                    subject="Password Reset Code",
                    message=f"Hello {user_doc.first_name}, your password reset code is: {otp}",
                    now=True,
                )

        return api_response(
            message="If a user with this email/phone exists, a password reset code has been sent.")
    except Exception:
        # For security, always return success
        return api_response(
            message="If a user with this email/phone exists, a password reset code has been sent.")


@frappe.whitelist(allow_guest=True)
def forgot_password_confirm(email: Any, verify_code: Any, password: Any=None) -> Any:
    """
    The forgot_password_confirm function is used to confirm a password reset using a verification code or token. It takes three parameters: email, verify_code, and an optional password. The email parameter can be either the email address or the phone number used for the password reset. The verify_code parameter is the verification code or token sent to the user. If the password parameter is provided, the function will update the user's password to the specified value after verifying the code. The function returns a response indicating whether the verification was successful, the password was updated, or an error occurred.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Confirm password reset using a verification code (OTP) or token.
    'email' can be the email address OR the phone number used for reset.
    """
    try:
        is_phone = email.startswith("+") or email.isdigit()
        cached_otp = frappe.cache.get_value(f"password_reset_otp:{email}")
        if not cached_otp or cached_otp != verify_code:
            return api_response(
                message="Invalid or expired verification code", status_code=400
            )

        if is_phone:
            user_name = frappe.db.get_value("User", {"phone": email}, "name")
        else:
            user_name = frappe.db.get_value("User", {"email": email}, "name")

        if not user_name:
            return api_response(message="User not found", status_code=404)

        if password:
            user_doc = frappe.get_doc("User", user_name)
            user_doc.set("new_password", password)
            user_doc.reset_password_key = None  # Clear token after use
            user_doc.save(ignore_permissions=True)
            if is_phone:
                frappe.cache.delete_value(f"password_reset_otp:{email}")
            return api_response(message="Password updated successfully")

        return api_response(message="Code verified")
    except Exception as e:
        return api_response(message=str(e), status_code=500)


@frappe.whitelist(allow_guest=True)
def login_with_google(email: Any, display_name: Any, id: Any, avatar: Any=None) -> Any:
    """
    The login_with_google function is a social login endpoint that links accounts by email or creates new ones. It takes four parameters: email, display_name, id, and an optional avatar. The email parameter is the user's email address, display_name is the user's full name, id is a unique identifier, and avatar is the user's profile picture. If the email address is not provided, the function returns an error response. If a user with the provided email address does not exist, a new user account is created with the provided information. If a user with the provided email address already exists, their account is updated with the provided avatar if it is not already set. The function then generates or retrieves a secret for API authentication and returns a login response with an access token and user information.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Social login endpoint. Links accounts by email or creates new ones.
    """
    if not email:
        return api_response(message="Email is required", status_code=400)

    user_name = frappe.db.get_value("User", {"email": email}, "name")

    if not user_name:
        # Create new user
        names = display_name.split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""

        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "user_image": avatar,
                "enabled": 1,
                "send_welcome_email": 0,
                "roles": [{"role": "PaaS User"}, {"role": "user"}],
            }
        )
        # Generate a random password for social users
        user.set("new_password", frappe.generate_hash(length=12))
        user.insert(ignore_permissions=True)
        user_name = user.name
    else:
        user = frappe.get_doc("User", user_name)
        if avatar and not user.user_image:
            user.user_image = avatar
            user.save(ignore_permissions=True)

    # Generate or retrieve secret for API authentication
    api_secret = user.get_password("api_secret")
    if not user.api_key or not api_secret:
        api_secret = frappe.generate_hash(length=15)
        user.api_key = frappe.generate_hash(length=15)
        user.api_secret = api_secret
        user.save(ignore_permissions=True)

    token = f"{user.api_key}:{api_secret}"

    return api_response(
        message="Logged In via Google",
        data={
            "access_token": token,
            "token_type": "Bearer",
            "user": {
                "id": user.name,
                "email": user.email,
                "firstname": user.first_name,
                "lastname": user.last_name,
                "phone": user.phone,
                "role": "user",
                "active": 1,
                "img": user.user_image,
            },
        },
    )


@frappe.whitelist()
def search_user(name: str, page: int=1, limit: int=20, lang: str='en') -> Any:
    """
    Search for users by name, email, or phone.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    t_user = frappe.qb.DocType("User")
    query = (
        frappe.qb.from_(t_user)
        .select(t_user.name, t_user.full_name, t_user.user_image)
        .where(t_user.enabled == 1)
        .where(t_user.name != "Guest")
        .where(t_user.name != "Administrator")
    )

    from frappe.query_builder.functions import Function

    to_tsvector = Function("to_tsvector")
    plainto_tsquery = Function("plainto_tsquery")
    tsq = plainto_tsquery("english", name)

    query = query.where(
        (to_tsvector("english", t_user.first_name).matches(tsq))
        | (to_tsvector("english", t_user.last_name).matches(tsq))
        | (to_tsvector("english", t_user.email).matches(tsq))
        | (to_tsvector("english", t_user.phone).matches(tsq))
    )

    users = query.limit(limit).offset((page - 1) * limit).run(as_dict=True)
    return api_response(data=users)


@frappe.whitelist()
def send_wallet_balance(amount: float, name_or_number: str, message: str=None, lang: str='en') -> Any:
    """
    The send_wallet_balance function transfers the specified amount from the current user's wallet to another user's wallet. It takes four parameters: amount, which is the amount to be transferred as a float, name_or_number, which is the recipient's phone number or email address as a string, message, an optional string parameter for a custom message, and lang, an optional string parameter for the language, defaulting to English if not provided. The function first checks if the sender is logged in and has a wallet, then verifies the recipient's existence and wallet. It ensures the sender has sufficient balance before performing the transfer and logs the transaction history for both the sender and the recipient.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Transfers wallet balance from current user to another user.
    """
    sender = frappe.session.user
    if sender == "Guest":
        frappe.throw("You must be logged in to transfer funds.")

    # Find recipient
    recipient = frappe.db.get_value("User", {"phone": name_or_number}, "name")
    if not recipient:
        recipient = frappe.db.get_value(
            "User", {"email": name_or_number}, "name"
        )

    if not recipient:
        frappe.throw("Recipient not found.")

    if recipient == sender:
        frappe.throw("You cannot send money to yourself.")

    # Ensure sender has a wallet
    sender_wallet_name = frappe.db.get_value(
        "Wallet", {"user": sender}, "name"
    )
    if not sender_wallet_name:
        frappe.throw("You do not have a wallet.")

    sender_wallet = frappe.get_doc("Wallet", sender_wallet_name)

    # Check balance
    amount_val = float(amount)
    if sender_wallet.balance < amount_val:
        frappe.throw("Insufficient balance.")

    # Ensure recipient has a wallet (get or create)
    recipient_wallet_name = frappe.db.get_value(
        "Wallet", {"user": recipient}, "name"
    )
    if not recipient_wallet_name:
        recipient_wallet = frappe.get_doc(
            {"doctype": "Wallet", "user": recipient, "balance": 0}
        ).insert(ignore_permissions=True)
        recipient_wallet_name = recipient_wallet.name
    else:
        recipient_wallet = frappe.get_doc("Wallet", recipient_wallet_name)

    # Atomic Transfer
    sender_wallet.balance -= amount_val
    recipient_wallet.balance += amount_val

    sender_wallet.save(ignore_permissions=True)
    recipient_wallet.save(ignore_permissions=True)

    # Log History – Sender
    frappe.get_doc(
        {
            "doctype": "Wallet History",
            "wallet": sender_wallet_name,
            "transaction_type": "Withdraw",
            "amount": amount_val,
            "status": "Processed",
            "description": f"Transfer to {recipient}",
        }
    ).insert(ignore_permissions=True)

    # Log History – Recipient
    frappe.get_doc(
        {
            "doctype": "Wallet History",
            "wallet": recipient_wallet_name,
            "transaction_type": "Topup",
            "amount": amount_val,
            "status": "Processed",
            "description": f"Transfer from {sender}",
        }
    ).insert(ignore_permissions=True)

    return {"status": "success", "message": "Funds transferred successfully."}


@frappe.whitelist()
def update_profile_image(image: str) -> Any:
    """
    Updates the user's profile image.
    Alias/Wrapper for update_profile logic specific to image.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return update_profile(images=image)


@frappe.whitelist()
def get_user_membership() -> Any:
    """
    Retrieves the active membership for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your membership.",
            frappe.AuthenticationError,
        )

    user_membership = frappe.get_all(
        "User Membership",
        filters={"user": user, "is_active": 1},
        fields=["name", "membership", "start_date", "end_date"],
        order_by="end_date desc",
        limit=1,
    )

    if not user_membership:
        return None

    return user_membership[0]


@frappe.whitelist()
def get_user_membership_history() -> Any:
    """
    Retrieves the membership history for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your membership history.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "User Membership",
        filters={"user": user},
        fields=["name", "membership", "start_date", "end_date", "is_active"],
        order_by="end_date desc",
    )


@frappe.whitelist()
def get_user_parcel_orders() -> Any:
    """
    Retrieves the parcel order history for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your parcel orders.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "Parcel Order",
        filters={"user": user},
        fields=["name", "status", "total_price", "delivery_date"],
        order_by="creation desc",
        ignore_permissions=True,
    )


@frappe.whitelist()
def get_user_parcel_order(name: Any) -> Any:
    """
    Retrieves a single parcel order for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your parcel orders.",
            frappe.AuthenticationError,
        )

    parcel_order = frappe.get_doc("Parcel Order", name)
    if parcel_order.user != user:
        frappe.throw(
            "You are not authorized to view this parcel order.",
            frappe.PermissionError,
        )

    return parcel_order.as_dict()


@frappe.whitelist()
def get_user_addresses() -> Any:
    """
    Retrieves the list of addresses for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your addresses.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "User Address",
        filters={"user": user},
        fields=["name", "title", "address", "location", "active"],
    )


@frappe.whitelist()
def get_user_address(name: Any) -> Any:
    """
    Retrieves a single address for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your addresses.",
            frappe.AuthenticationError,
        )

    address = frappe.get_doc("User Address", name)
    if address.user != user:
        frappe.throw(
            "You are not authorized to view this address.",
            frappe.PermissionError,
        )

    return address.as_dict()


@frappe.whitelist()
def add_user_address(address_data: Any) -> Any:
    """
    Adds a new address for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(address_data, str):
        address_data = json.loads(address_data)

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to add an address.",
            frappe.AuthenticationError,
        )

    address = frappe.get_doc(
        {
            "doctype": "User Address",
            "user": user,
            "title": address_data.get("title"),
            "address": json.dumps(address_data.get("address")),
            "location": json.dumps(address_data.get("location")),
            "active": address_data.get("active", 1),
        }
    )
    address.insert(ignore_permissions=True)
    return address.as_dict()


@frappe.whitelist()
def update_user_address(name: Any, address_data: Any) -> Any:
    """
    Updates an existing address for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(address_data, str):
        address_data = json.loads(address_data)

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update an address.",
            frappe.AuthenticationError,
        )

    address = frappe.get_doc("User Address", name)
    if address.user != user:
        frappe.throw(
            "You are not authorized to update this address.",
            frappe.PermissionError,
        )

    address.title = address_data.get("title", address.title)
    address.address = json.dumps(address_data.get("address", address.address))
    address.location = json.dumps(
        address_data.get("location", address.location)
    )
    address.active = address_data.get("active", address.active)
    address.save(ignore_permissions=True)
    return address.as_dict()


@frappe.whitelist()
def delete_user_address(name: Any) -> Any:
    """
    Deletes an address for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to delete an address.",
            frappe.AuthenticationError,
        )

    address = frappe.get_doc("User Address", name)
    if address.user != user:
        frappe.throw(
            "You are not authorized to delete this address.",
            frappe.PermissionError,
        )

    frappe.delete_doc("User Address", name, ignore_permissions=True)
    return {"status": "success", "message": "Address deleted successfully."}


@frappe.whitelist()
def set_active_address(name: Any) -> Any:
    """
    Sets the given address as the active address for the currently
    logged-in user, clearing the active flag on their other addresses.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to set an active address.",
            frappe.AuthenticationError,
        )

    address = frappe.get_doc("User Address", name)
    if address.user != user:
        frappe.throw(
            "You are not authorized to update this address.",
            frappe.PermissionError,
        )

    other_active = frappe.get_all(
        "User Address",
        filters={"user": user, "name": ["!=", address.name], "active": 1},
        pluck="name",
    )
    for other_name in other_active:
        frappe.db.set_value("User Address", other_name, "active", 0)

    address.active = 1
    address.save(ignore_permissions=True)
    return address.as_dict()


@frappe.whitelist()
def get_referral_details() -> Any:
    """
    Retrieves referral program details for the currently logged-in user.

    No referral program is implemented in this backend, so this endpoint
    reports the feature as not configured (a null referral payload)
    instead of failing with a 404. Clients should treat a null "referral"
    value as "feature absent".
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view referral details.",
            frappe.AuthenticationError,
        )

    return {
        "referral": None,
        "detail": "No referral program is configured.",
    }


@frappe.whitelist()
def get_user_invites() -> Any:
    """
    Retrieves the list of invites for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your invites.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "Invitation",
        filters={"user": user},
        fields=["name", "shop", "role", "status"],
    )


@frappe.whitelist()
def create_invite(shop: Any, user: Any, role: Any) -> Any:
    """
    Creates a new invite.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # In a real application, we would have more permission checks here.
    # For example, only a shop owner or manager should be able to invite users.
    # For now, we will assume the user has the necessary permissions.

    invite = frappe.get_doc(
        {
            "doctype": "Invitation",
            "shop": shop,
            "user": user,
            "role": role,
            "status": "New",
        }
    )
    invite.insert(ignore_permissions=True)
    return invite.as_dict()


@frappe.whitelist()
def update_invite_status(name: Any, status: Any) -> Any:
    """
    Updates the status of an invite.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update an invite.",
            frappe.AuthenticationError,
        )

    invite = frappe.get_doc("Invitation", name)
    if invite.user != user:
        frappe.throw(
            "You are not authorized to update this invite.",
            frappe.PermissionError,
        )

    if status not in ["Accepted", "Rejected"]:
        frappe.throw("Invalid status. Must be 'Accepted' or 'Rejected'.")

    invite.status = status
    invite.save(ignore_permissions=True)
    return invite.as_dict()


@frappe.whitelist()
def get_user_wallet() -> Any:
    """
    Retrieves the wallet for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your wallet.",
            frappe.AuthenticationError,
        )

    wallet = frappe.get_doc("Wallet", {"user": user})
    return api_response(data=wallet.as_dict())


@frappe.whitelist()
def get_wallet_history(start: Any=0, limit: Any=20) -> Any:
    """
    Retrieves the wallet history for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your wallet history.",
            frappe.AuthenticationError,
        )

    wallet = frappe.get_doc("Wallet", {"user": user})
    history = frappe.get_all(
        "Wallet History",
        filters={"wallet": wallet.name},
        fields=["name", "transaction_type", "amount", "status", "creation"],
        order_by="creation desc",
        offset=start,
        limit=limit,
    )
    return api_response(data=history)


@frappe.whitelist()
def export_orders() -> Any:
    """
    Exports all orders for the current user to a CSV file.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to export orders.",
            frappe.AuthenticationError,
        )

    orders = frappe.get_all(
        "Order",
        filters={"user": user},
        fields=["name", "shop", "total_price", "status", "creation"],
        order_by="creation desc",
    )

    if not orders:
        return []

    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(["Order ID", "Shop", "Total Price", "Status", "Date"])

    # Write the data rows
    for order in orders:
        writer.writerow(
            [
                order.name,
                order.shop,
                order.total_price,
                order.status,
                order.creation,
            ]
        )

    # Set the response headers for CSV download
    frappe.local.response.filename = "orders.csv"
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = "csv"


@frappe.whitelist()
def register_device_token(device_token: str, provider: str) -> Any:
    """
    Registers a new device token for the current user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to register a device token.",
            frappe.AuthenticationError,
        )

    if not device_token or not provider:
        frappe.throw("Device token and provider are required.")

    if frappe.db.exists("Device Token", {"device_token": device_token}):
        return api_response(message="Device token already registered.")

    frappe.get_doc(
        {
            "doctype": "Device Token",
            "user": user,
            "device_token": device_token,
            "provider": provider,
        }
    ).insert(ignore_permissions=True)
    return api_response(message="Device token registered successfully.")


@frappe.whitelist()
def get_user_transactions(start: Any=0, limit: Any=20) -> Any:
    """
    Retrieve the list of transactions for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your transactions.",
            frappe.AuthenticationError,
        )

    transactions = frappe.get_all(
        "Transaction",
        filters={"user": user},
        fields=[
            "name",
            "user",
            "amount",
            "status",
            "payable_type",
            "payable_id",
            "creation",
        ],
        order_by="creation desc, name desc",
        offset=start,
        limit=limit,
        ignore_permissions=True,
    )
    return api_response(data=transactions)


@frappe.whitelist()
def get_user_shop() -> Any:
    """
    Retrieves the shop owned by the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your shop.",
            frappe.AuthenticationError,
        )

    try:
        shop_name = frappe.db.get_value("Shop", {"user": user}, "name")
        if not shop_name:
            return api_response(data=None)
        return api_response(data=frappe.get_doc("Shop", shop_name).as_dict())
    except frappe.DoesNotExistError:
        return api_response(data=None)


@frappe.whitelist()
def update_seller_shop(shop_data: Any) -> Any:
    """
    Updates the shop owned by the currently logged-in seller.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if isinstance(shop_data, str):
        shop_data = json.loads(shop_data)

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your shop.",
            frappe.AuthenticationError,
        )

    shop_name = frappe.db.get_value("Shop", {"user": user}, "name")
    if not shop_name:
        frappe.throw("You do not own a shop.", frappe.PermissionError)

    shop = frappe.get_doc("Shop", shop_name)

    # List of fields that a user is allowed to update
    updatable_fields = ["phone", "location", "open", "shop_name"]

    # Handle name change (Rename Doc) BEFORE other updates
    new_shop_name = shop_data.get("shop_name") or shop_data.get("title")
    if new_shop_name and new_shop_name != shop.name:
        # Switch to admin to bypass permission check for rename
        current_user = frappe.session.user
        frappe.set_user("Administrator")
        try:
            new_name = frappe.rename_doc("Shop", shop.name, new_shop_name)
            shop = frappe.get_doc("Shop", new_name)
        finally:
            frappe.set_user(current_user)

    for key, value in shop_data.items():
        if key in updatable_fields:
            shop.set(key, value)

    # Handle legacy title mapping
    if "title" in shop_data:
        shop.shop_name = shop_data.get("title")

    shop.save(ignore_permissions=True)
    return api_response(data=shop.as_dict())


@frappe.whitelist()
def update_user_shop(shop_data: Any) -> Any:
    """
    Alias for update_seller_shop (for backward compatibility/testing)
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return update_seller_shop(shop_data)


@frappe.whitelist()
def get_user_request_models(start: Any=0, limit: Any=20) -> Any:
    """
    Retrieves the list of request models for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your request models.",
            frappe.AuthenticationError,
        )

    models = frappe.get_all(
        "Request Model",
        filters={"created_by_user": user},
        fields=["name", "model_type", "model", "status", "created_at"],
        order_by="creation desc",
        offset=start,
        limit=limit,
    )
    return api_response(data=models)


@frappe.whitelist()
def create_request_model(model_type: Any, model_id: Any, data: Any) -> Any:
    """
    Creates a new request model.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to create a request model.",
            frappe.AuthenticationError,
        )

    request_model = frappe.get_doc(
        {
            "doctype": "Request Model",
            "model_type": model_type,
            "model": model_id,
            "data": data,
            "created_by_user": user,
            "status": "Pending",
        }
    )
    request_model.insert(ignore_permissions=True)
    return request_model.as_dict()


@frappe.whitelist()
def get_user_tickets(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """
    Retrieves the list of tickets for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your tickets.",
            frappe.AuthenticationError,
        )

    return frappe.get_all(
        "Ticket",
        filters={"created_by_user": user, "parent_ticket": None},
        # Only get parent tickets
        fields=["name", "subject", "status", "creation"],
        order_by="creation desc",
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_user_ticket(name: Any) -> Any:
    """
    Retrieves a single ticket and its replies for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your tickets.",
            frappe.AuthenticationError,
        )

    ticket = frappe.get_doc("Ticket", name)
    if ticket.created_by_user != user:
        frappe.throw(
            "You are not authorized to view this ticket.",
            frappe.PermissionError,
        )

    replies = frappe.get_all(
        "Ticket",
        filters={"parent_ticket": name},
        fields=["name", "content", "created_by_user", "creation"],
    )

    ticket_dict = ticket.as_dict()
    ticket_dict["replies"] = replies
    return ticket_dict


@frappe.whitelist()
def create_ticket(subject: Any, content: Any, order_id: Any=None) -> Any:
    """
    Creates a new ticket.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to create a ticket.",
            frappe.AuthenticationError,
        )

    ticket = frappe.get_doc(
        {
            "doctype": "Ticket",
            "uuid": str(uuid.uuid4()),
            "subject": subject,
            "content": content,
            "order": order_id,
            "created_by_user": user,
            "user": user,
            "status": "Open",
            "type": "order" if order_id else "general",
        }
    )
    ticket.insert(ignore_permissions=True)
    return ticket.as_dict()


@frappe.whitelist()
def reply_to_ticket(name: Any, content: Any) -> Any:
    """
    Adds a reply to an existing ticket.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to reply to a ticket.",
            frappe.AuthenticationError,
        )

    parent_ticket = frappe.get_doc("Ticket", name)
    if (
        parent_ticket.created_by_user != user
        and "System Manager" not in frappe.get_roles(user)
    ):
        frappe.throw(
            "You are not authorized to reply to this ticket.",
            frappe.PermissionError,
        )

    reply = frappe.get_doc(
        {
            "doctype": "Ticket",
            "uuid": str(uuid.uuid4()),
            "parent_ticket": name,
            "subject": f"Re: {parent_ticket.subject}",
            "content": content,
            "created_by_user": user,
            "user": user,
            "status": "Answered",
        }
    )
    reply.insert(ignore_permissions=True)

    # Update parent ticket status
    parent_ticket.status = "Answered"
    parent_ticket.save(ignore_permissions=True)

    return reply.as_dict()


@frappe.whitelist()
def get_user_profile() -> Any:
    """
    The get_user_profile function retrieves the profile information for the currently logged-in user. It does not require any parameters to be passed. The function returns a dictionary containing the user's first name, last name, email, phone number, birth date, location, gender, and ringfenced balance. If the user is not logged in, it raises an AuthenticationError with a message prompting the user to log in.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Retrieves the profile information for the currently logged-in user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your profile.",
            frappe.AuthenticationError,
        )

    user_doc = frappe.get_doc("User", user)

    return {
        "first_name": user_doc.first_name,
        "last_name": user_doc.last_name,
        "email": user_doc.email,
        "phone": user_doc.phone,
        "birth_date": user_doc.birth_date,
        "location": user_doc.location,
        "gender": user_doc.gender,
        "ringfenced_balance": user_doc.ringfenced_balance or 0,
    }


@frappe.whitelist()
def update_user_profile(profile_data: Any) -> Any:
    """
    The update_user_profile function updates the profile information for the currently logged-in user. It takes one parameter, profile_data, which is a JSON string or a dictionary containing the new profile data. The function checks if the user is logged in and then updates the allowed fields in the user's profile, including first name, last name, phone, birth date, location, and gender. If the update is successful, it returns a dictionary with a status of success and a message indicating that the profile has been updated successfully.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    trace_id = None
    """
    Updates the profile information for the currently logged-in user.
    """
    if isinstance(profile_data, str):
        profile_data = json.loads(profile_data)

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your profile.",
            frappe.AuthenticationError,
        )

    user_doc = frappe.get_doc("User", user)

    # List of fields that a user is allowed to update
    updatable_fields = [
        "first_name",
        "last_name",
        "phone",
        "birth_date",
        "location",
        "gender",
    ]

    for key, value in profile_data.items():
        if key in updatable_fields:
            user_doc.set(key, value)

    user_doc.save(ignore_permissions=True)

    return {"status": "success", "message": "Profile updated successfully."}


@frappe.whitelist()
def get_user_order_refunds(page: Any=1) -> Any:
    """
    The get_user_order_refunds function retrieves a list of order refunds associated with the currently logged-in user. It takes an optional page parameter, which defaults to 1, allowing for pagination of the results with 10 refunds per page. The function returns a list of refunds, each containing the refund name, order, cause, and status, sorted in descending order by creation date. If the user is not logged in, it throws an error requiring the user to log in to view their refunds.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to view your refunds.")

    refunds = frappe.get_list(
        "Order Refund",
        filters={"user": user},
        fields=["name", "order", "cause", "status"],
        offset=(int(page) - 1) * 10,
        limit=10,
        order_by="creation desc",
    )
    return refunds


@frappe.whitelist()
def create_order_refund(order: Any, cause: Any) -> Any:
    """
    Creates a new order refund request.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to request a refund.",
            frappe.AuthenticationError,
        )

    # Check if the user owns the order
    order_doc = frappe.get_doc("Order", order)
    if order_doc.user != user:
        frappe.throw(
            "You are not authorized to request a refund for this order.",
            frappe.PermissionError,
        )

    refund = frappe.get_doc(
        {
            "doctype": "Order Refund",
            "user": user,
            "order": order,
            "cause": cause,
            "status": "Pending",
        }
    )
    refund.insert(ignore_permissions=True)
    return refund.as_dict()


@frappe.whitelist()
def get_user_notifications(start: Any=0, limit: Any=20) -> Any:
    """
    Retrieves the list of notifications for the currently logged-in user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your notifications.",
            frappe.AuthenticationError,
        )

    # The Notification doctype in Frappe is complex.
    # It is used for email alerts and other system notifications.
    # A simple way to get user-specific notifications is to look at the
    # Notification Log, which records when a notification is sent to a user.

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
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
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
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
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
            if doc.for_user == user or doc.owner == user:  # Check ownership
                doc.read = 1
                doc.save(ignore_permissions=True)

    return api_response(message="Notifications marked as read")


@frappe.whitelist()
def read_all_notifications() -> Any:
    """
    Marks all notifications as read for the current user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in.", frappe.AuthenticationError)

    logs = frappe.get_all(
        "Notification Log", filters={"for_user": user, "read": 0}
    )
    for log in logs:
        frappe.db.set_value("Notification Log", log.name, "read", 1)

    return api_response(message="All notifications marked as read")


@frappe.whitelist()
def read_one_notification(name: Any) -> Any:
    """
    Marks a single notification as read.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in.", frappe.AuthenticationError)

    if frappe.db.exists("Notification Log", name):
        doc = frappe.get_doc("Notification Log", name)
        # Verify it belongs to user ( Notification Log uses 'for_user' usually,
        # but sometimes owner)
        if hasattr(doc, "for_user") and doc.for_user == user:
            doc.read = 1
            doc.save(ignore_permissions=True)
        elif doc.owner == user:
            doc.read = 1
            doc.save(ignore_permissions=True)

    return api_response(message="Notification marked as read")


# ---------------------------------------------------------------------------
# BEGIN WEAK CONCEPTS PURE HELPERS (frappe-free)
# Pure-python aggregation and scoring for get_weak_concepts. This block must
# stay free of frappe (and any other non-stdlib) references so the logic can
# be unit-tested outside a bench: tests/test_weak_concepts_rules.py extracts
# and executes exactly this block. Keep the BEGIN/END marker comments intact.
# ---------------------------------------------------------------------------
from datetime import datetime

WEAK_CONCEPTS_WEIGHT_INCORRECT = 1.0
WEAK_CONCEPTS_WEIGHT_SKIPPED = 0.5
WEAK_CONCEPTS_RECENCY_HALF_LIFE_DAYS = 30.0

WEAK_CONCEPTS_DEFAULT_LIMIT = 20
WEAK_CONCEPTS_DEFAULT_OFFSET = 0
WEAK_CONCEPTS_DEFAULT_DAYS = 90


def _weak_concepts_to_int(value, default):
    """Coerce a query-string style value to int, falling back to default."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def clamp_weak_concepts_params(limit=None, offset=None, days=None):
    """
    Coerce and clamp pagination/window params.
    limit -> int in 1..100, offset -> int >= 0, days -> int in 1..365.
    Non-numeric input falls back to the defaults (20 / 0 / 90).
    """
    limit = _weak_concepts_to_int(limit, WEAK_CONCEPTS_DEFAULT_LIMIT)
    offset = _weak_concepts_to_int(offset, WEAK_CONCEPTS_DEFAULT_OFFSET)
    days = _weak_concepts_to_int(days, WEAK_CONCEPTS_DEFAULT_DAYS)
    limit = max(1, min(100, limit))
    offset = max(0, offset)
    days = max(1, min(365, days))
    return limit, offset, days


def humanize_subtopic_ref(ref):
    """quadratic_formula_derivation -> 'quadratic formula derivation'."""
    return (ref or "").replace("_", " ").strip()


def _weak_concepts_parse_dt(value):
    """Accept datetime or ISO-ish string (Frappe creation format)."""
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def aggregate_weak_concepts(
    rows,
    now,
    weight_incorrect=WEAK_CONCEPTS_WEIGHT_INCORRECT,
    weight_skipped=WEAK_CONCEPTS_WEIGHT_SKIPPED,
    half_life_days=WEAK_CONCEPTS_RECENCY_HALF_LIFE_DAYS,
):
    """
    Aggregate per-answer quiz result rows into weak-concept entries.

    rows: iterable of dicts with keys subtopic_ref, outcome, creation.
    now: aware/naive datetime matching the creation timestamps.

    Returns the FULL (unpaginated) sorted list of dicts:
      subtopic_ref, label, score, incorrect, skipped, correct, attempts,
      last_seen (ISO string).
    Subtopics whose rows are all Correct (no weak rows) are excluded.
    Sort: score desc, then last_seen desc, then subtopic_ref asc.
    """
    buckets = {}
    for row in rows or []:
        ref = (row.get("subtopic_ref") or "").strip()
        if not ref:
            continue
        created = _weak_concepts_parse_dt(row.get("creation"))
        bucket = buckets.setdefault(ref, {
            "subtopic_ref": ref,
            "incorrect": 0,
            "skipped": 0,
            "correct": 0,
            "attempts": 0,
            "score": 0.0,
            "_last_seen_dt": None,
        })
        bucket["attempts"] += 1
        outcome = (row.get("outcome") or "").strip().lower()
        weight = 0.0
        if outcome == "incorrect":
            bucket["incorrect"] += 1
            weight = weight_incorrect
        elif outcome == "skipped":
            bucket["skipped"] += 1
            weight = weight_skipped
        elif outcome == "correct":
            bucket["correct"] += 1
        if created is not None:
            if bucket["_last_seen_dt"] is None or created > bucket["_last_seen_dt"]:
                bucket["_last_seen_dt"] = created
            if weight:
                age_days = max((now - created).total_seconds(), 0.0) / 86400.0
                recency = 0.5 ** (age_days / half_life_days)
                bucket["score"] += weight * recency
        elif weight:
            # Row is weak but has no usable timestamp: count it with full
            # recency so it is never silently dropped.
            bucket["score"] += weight

    concepts = []
    for bucket in buckets.values():
        if bucket["incorrect"] == 0 and bucket["skipped"] == 0:
            continue  # all-correct subtopic: not weak
        last_seen_dt = bucket.pop("_last_seen_dt")
        bucket["last_seen"] = last_seen_dt.isoformat(sep=" ") if last_seen_dt else None
        bucket["label"] = humanize_subtopic_ref(bucket["subtopic_ref"])
        bucket["score"] = round(bucket["score"], 4)
        bucket["_sort_ts"] = last_seen_dt.timestamp() if last_seen_dt else float("-inf")
        concepts.append(bucket)

    concepts.sort(key=lambda c: (-c["score"], -c["_sort_ts"], c["subtopic_ref"]))
    for concept in concepts:
        concept.pop("_sort_ts", None)
    return concepts


def build_weak_concepts_response(rows, now, limit, offset, days, source_available=True):
    """Build the full endpoint payload: aggregate, then paginate."""
    concepts = aggregate_weak_concepts(rows, now) if source_available else []
    total = len(concepts)
    page = concepts[offset:offset + limit]
    return {
        "concepts": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "days": days,
        "source_available": bool(source_available),
    }
# ---------------------------------------------------------------------------
# END WEAK CONCEPTS PURE HELPERS
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_weak_concepts(limit: Any = 20, offset: Any = 0, days: Any = 90) -> Any:
    """
    Cross-session weak concepts for the currently logged-in student.

    Aggregates the student's own LMS Lesson Quiz Result rows (written
    per-answer by the lms module) across ALL sessions within the last `days`
    days, keyed by subtopic_ref. Incorrect answers weigh 1.0, skipped 0.5,
    with a 30-day-half-life recency decay. Subtopics answered entirely
    correctly are excluded. Returns refs plus a humanized `label` fallback
    (client may override labels from its session manifests).

    The LMS Lesson Quiz Result doctype ships with a different module bundle;
    when it is not installed the endpoint returns the normal shape with an
    empty list and source_available=false instead of failing.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your weak concepts.",
            frappe.AuthenticationError,
        )

    limit, offset, days = clamp_weak_concepts_params(limit, offset, days)

    try:
        source_available = bool(frappe.db.exists("DocType", "LMS Lesson Quiz Result"))
    except Exception:
        source_available = False

    from frappe.utils import add_days, now_datetime
    now = now_datetime()

    if not source_available:
        return api_response(data=build_weak_concepts_response(
            [], now, limit=limit, offset=offset, days=days,
            source_available=False,
        ))

    rows = frappe.get_all(
        "LMS Lesson Quiz Result",
        filters={
            "member": user,
            "creation": (">=", add_days(now, -days)),
        },
        fields=["subtopic_ref", "outcome", "creation"],
        limit_page_length=0,
        ignore_permissions=True,
    )

    return api_response(data=build_weak_concepts_response(
        rows, now, limit=limit, offset=offset, days=days,
        source_available=True,
    ))
