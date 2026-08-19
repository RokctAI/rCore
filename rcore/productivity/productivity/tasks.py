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

import frappe
import datetime

def send_weekly_goal_reminders():
    if frappe.conf.get("app_role") != "tenant": return
    if datetime.datetime.today().weekday() != 0:
        return
    active_goals = frappe.get_all("Personal Mastery Goal", filters={"status": ["not in", ["Achieved", "Cancelled"]]}, fields=["name", "title"])
    for goal in active_goals:
        try:
            frappe.log_error(
                message=f"Monday morning goal check-in: How is your progress on your goal '{goal.title}'? Set your intentions for the week!",
                title="Weekly Goal Check-In"
            )
        except Exception as e:
            frappe.log_error(f"Failed to trigger goal reminder for {goal.name}: {e}")
    frappe.db.commit()

def send_friday_wins_reminders():
    if frappe.conf.get("app_role") != "tenant": return
    if datetime.datetime.today().weekday() != 4:
        return
    try:
        frappe.log_error(
            message="Friday Wins prep: What were your top wins and achievements this week? Take a moment to reflect and log them with ROK!",
            title="Friday Wins Preparation"
        )
    except Exception as e:
        frappe.log_error(f"Failed to trigger Friday Wins reminder: {e}")
    frappe.db.commit()
