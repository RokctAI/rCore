import requests
import time
import json
import os

# CONFIGURATION
BASE_URL = "http://localhost:8001"  # Adjust port if needed
API_KEY = "YOUR_JULES_API_KEY"  # <--- REPLACE THIS
API_SECRET = "YOUR_FRAPPE_API_SECRET"  # <--- REPLACE THIS (if needed for auth)
FRAPPE_API_KEY = "YOUR_FRAPPE_API_KEY"  # <--- REPLACE THIS

HEADERS = {"Authorization": f"token {FRAPPE_API_KEY}:{API_SECRET}" if FRAPPE_API_KEY !=
           "YOUR_FRAPPE_API_KEY" else None}


def verify_interactive_flow():
    if API_KEY == "YOUR_JULES_API_KEY":
        print("❌ Please set your JULES_API_KEY in the script.")
        return

    print("🚀 Starting API Verification (Interactive Jules)...")

    # 1. Create Session
    print("\n1. Creating Session (require_approval=True)...")
    url = f"{BASE_URL}/api/method/brain.api.start_jules_session"
    payload = {
        "prompt": "Create a file named 'verification.txt'.",
        "source_repo": "sources/github/RendaniSinyage/RokctAI_frontend",
        "api_key": API_KEY,
        "require_approval": True,
        "title": "API Verification"
    }

    try:
        resp = requests.post(url, json=payload, headers=HEADERS)
        if resp.status_code != 200:
            print(f"❌ Creation Failed: {resp.text}")
            return

        data = resp.json().get("message", {})
        session_id = data.get("name")
        print(f"✅ Session Created: {session_id}")
    except Exception as e:
        print(f"❌ Request Error: {e}")
        return

    # 2. Wait for Approval State
    print("\n2. Waiting for AWAITING_PLAN_APPROVAL...")
    status_url = f"{BASE_URL}/api/method/brain.api.get_jules_status"

    for i in range(20):
        resp = requests.post(
            status_url,
            json={
                "session_id": session_id,
                "api_key": API_KEY},
            headers=HEADERS)
        state = resp.json().get("message", {}).get("state")
        print(f"   [{i + 1}/20] State: {state}")

        if state == "AWAITING_PLAN_APPROVAL":
            print("✅ Ready for approval!")
            break
        elif state in ["FAILED", "ERROR"]:
            print(f"❌ Failed: {state}")
            return
        time.sleep(5)

    # 3. Approve Plan
    print("\n3. Approving Plan...")
    vote_url = f"{BASE_URL}/api/method/brain.api.vote_on_plan"
    requests.post(
        vote_url,
        json={
            "session_id": session_id,
            "action": "approve",
            "api_key": API_KEY},
        headers=HEADERS)
    print("✅ Approval sent.")

    # 4. Cleanup
    print("\n4. Cleaning Up...")
    requests.post(
        f"{BASE_URL}/api/method/brain.api.delete_jules_session",
        json={
            "session_id": session_id,
            "api_key": API_KEY},
        headers=HEADERS)
    print("✅ Session Deleted.")


if __name__ == "__main__":
    verify_interactive_flow()
