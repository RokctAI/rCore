# API Reference: tasks

Source file: `rcore/tasks.py`

## Documented Module Functions

### `def update_storage_usage()`
raw_sql

### `def disable_expired_support_users()`
Disables expired support user accounts. Tenant context trace.

### `def manage_daily_tenders()`
Fetches new tenders (Stimuli) from the control panel. Tenant context trace.

### `def manage_daily_funding()`
Fetches new Grants and Equity opportunities (Neurotrophins) from the control panel.

### `def check_invoice_payments()`
Automated payment reminders. Checks all unpaid and overdue Sales Invoices
and triggers reminders/system logs.

### `def pick_proactive_question()`
Picks a random active question from the Question Bank DocType
and triggers a system notification/log or logs it under ToDos.

### `def send_weekly_goal_reminders()`
Weekly goal cron. Triggers Monday morning check-in prompts for active Personal Mastery Goals.

### `def send_friday_wins_reminders()`
Friday Wins Chron. Triggers prompts to capture achievement logs / wins every Friday afternoon.

### `def archive_inactive_vault_files()`
90-Day vault file archiving. Archives/deletes files 90 days post-cancel of a subscription. Tenant context trace.

### `def check_protocol_99_sequences()`
Protocol 99 sequence: WhatsApp alerts and 6h vault release.
Checks active sequences and releases vault packages after 6 hours.

### `def tag_engram_pillars(doc, method=None)`
Cross-pillar tagging. Automatically tags engrams based on text classification.

### `def archive_low_score_engrams()`
Engram scoring & expiry. Archives engrams older than 1 year with low score.
