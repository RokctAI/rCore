from rcore.api.auth import login
from rcore.api.brain import semantic_search, query, search, record_event, get_event_interval
from rcore.api.plan_builder import get_available_models, perform_bootstrap_secrets_handshake, ensure_startup_os_core, commit_onboarding_answers, generate_alive_cv_pdf, generate_strategic_alignment_report, commit_plan, chat_with_rok, summarize_chat_session
from rcore.api.setup import update_naming_series

# Alias to support legacy rcore.api.rcore.* whitelist hooks in hooks.py
from rcore.api import brain as rcore
