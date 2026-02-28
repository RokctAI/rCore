# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe
import time
import json


def verify_interactive_flow():
    print("🚀 Starting Interactive Verification...")

    # 1. Create Session with Approval Required
    print("\n1. Creating Session (require_approval=True)...")
    try:
        session = frappe.call(
            "brain.api.start_jules_session",
            prompt="Create a simple 'hello_world.txt' file.",
            source_repo="sources/github/RendaniSinyage/RokctAI_frontend",  # Using a known repo
            require_approval=True,
            title="Interactive Test"
        )
        session_id = session.get("name")  # "sessions/..."
        print(f"✅ Session Created: {session_id}")
    except Exception as e:
        print(f"❌ Creation Failed: {e}")
        return

    # 2. Wait for AWAITING_PLAN_APPROVAL
    print("\n2. Waiting for Plan Approval State...")
    max_retries = 20
    for i in range(max_retries):
        status_data = frappe.call(
            "brain.api.get_jules_status",
            session_id=session_id)
        state = status_data.get("state")
        print(f"   [{i + 1}/{max_retries}] State: {state}")

        if state == "AWAITING_PLAN_APPROVAL":
            print("✅ Session is ready for approval!")
            break
        elif state in ["FAILED", "CANCELLED", "ERROR"]:
            print(f"❌ Session Failed prematurely: {state}")
            return

        time.sleep(5)
    else:
        print("❌ Timeout waiting for AWAITING_PLAN_APPROVAL")
        return

    # 3. Approve Plan
    print("\n3. Approving Plan...")
    try:
        frappe.call(
            "brain.api.vote_on_plan",
            session_id=session_id,
            action="approve"
        )
        print("✅ Plan Approved command sent.")
    except Exception as e:
        print(f"❌ Approval Failed: {e}")
        return

    # 4. Watch for Progress (State Change)
    print("\n4. Verifying State Change...")
    time.sleep(5)  # Give it a moment
    status_data = frappe.call(
        "brain.api.get_jules_status",
        session_id=session_id)
    print(f"   Current State: {status_data.get('state')}")
    if status_data.get("state") != "AWAITING_PLAN_APPROVAL":
        print("✅ State changed successfully.")
    else:
        print("⚠️ State didn't change immediately (might take a moment).")

    # 5. Send User Message
    print("\n5. Sending User Message...")
    try:
        frappe.call(
            "brain.api.send_jules_message",
            session_id=session_id,
            message="Please also make sure the file contains a timestamp."
        )
        print("✅ Message Sent.")
    except Exception as e:
        print(f"❌ Message Send Failed: {e}")

    # 6. Verify Message in Activities
    print("\n6. Verifying Message in Activities...")
    time.sleep(5)
    activities = frappe.call(
        "brain.api.get_jules_activities",
        session_id=session_id)

    found = False
    for act in activities:
        # Check for userMessaged event
        if "userMessaged" in act or (act.get("originator") == "user"):
            print(f"   Found User Message Activity: {act.get('description')}")
            found = True
            break

    if found:
        print("✅ User Message Verified in History.")
    else:
        print("⚠️ User Message not found in immediate history (might be lagged).")

    # 7. Cleanup
    print("\n7. Cleaning Up...")
    frappe.call("brain.api.delete_jules_session", session_id=session_id)
    print("✅ Session Deleted.")


if __name__ == "__main__":
    verify_interactive_flow()
