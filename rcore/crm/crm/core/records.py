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

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Pure, frappe-free helpers shared by the CRM controllers.

This module must stay importable without a Frappe environment so the SDK's
unit tests (src/tests) can exercise the business rules directly.
"""

from datetime import datetime

UNNAMED_LEAD = "Unnamed Lead"


def build_full_name(salutation=None, first_name=None, middle_name=None, last_name=None):
    """Join the non-empty name parts into a display name.

    Mirrors Lead.set_full_name: only called when first_name is set.
    """
    return " ".join(part for part in (salutation, first_name, middle_name, last_name) if part)


def derive_lead_name(lead_name=None, organization=None, email=None):
    """Fallback chain for a lead's display name.

    Returns the existing lead_name if set, else the organization, else the
    local part of the email address, else the "Unnamed Lead" placeholder.
    """
    if lead_name:
        return lead_name
    if organization:
        return organization
    if email:
        return email.split("@")[0]
    return UNNAMED_LEAD


def resolve_primary_contact_details(contacts):
    """Given deal contact rows (dicts with is_primary/email/mobile_no/phone),
    return the (email, mobile_no, phone) tuple of the primary contact.

    Empty strings are returned when there are no contacts or no primary row.
    Raises ValueError when more than one row is flagged primary.
    """
    if not contacts:
        return ("", "", "")

    primaries = [c for c in contacts if c.get("is_primary")]
    if len(primaries) > 1:
        raise ValueError("Only one contact can be set as primary.")
    if not primaries:
        return ("", "", "")

    primary = primaries[0]

    def clean(value):
        return value.strip() if value else ""

    return (clean(primary.get("email")), clean(primary.get("mobile_no")), clean(primary.get("phone")))


def mark_primary_contact(contacts, contact=None):
    """Return the row-index that should be primary, or None.

    Mirrors Opportunity.set_primary_contact: a single contact row is implicitly
    primary; otherwise the row matching `contact` wins.
    """
    if not contacts:
        return None
    if contact is None and len(contacts) == 1:
        return 0
    if contact is not None:
        for index, row in enumerate(contacts):
            if row.get("contact") == contact:
                return index
    return None


def get_duration_seconds(from_date, to_date):
    """Seconds elapsed between two datetimes (or ISO strings)."""
    if not isinstance(from_date, datetime):
        from_date = datetime.fromisoformat(str(from_date))
    if not isinstance(to_date, datetime):
        to_date = datetime.fromisoformat(str(to_date))
    return (to_date - from_date).total_seconds()


def seconds_to_duration(seconds):
    """Format a duration in seconds as a compact "1h 2m 3s" string."""
    if not seconds:
        return "0s"

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = (seconds % 3600) % 60

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs:
        parts.append(f"{secs}s")
    return " ".join(parts) if parts else "0s"
