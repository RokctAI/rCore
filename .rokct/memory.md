# Agent Memory & Lessons Learned

**Rule**: Before asking a question or starting a task, the Agent **MUST** read this file to check for past lessons or user preferences.

## User Profiles
*   **Ray**:
    *   **Safe ID**: sinyage.1aedb8 (Used for filenames)
    *   **Role/Preferences**: Developer, Admin
*   *(Agent: Add new users here as they appear)*

## Global Preferences
*   **Session Retention**: [Forever] (Options: Forever, 1 Month, 1 Week)
*   **Checkpoint Policy**: [Value] (Options: Frequent, Manual) -> *Set 'Frequent' for Cloud Agents*
*   [Active] Prefer "Frappe" for backend.
*   [Active] Prefer "Next.js + AI SDK" for frontend.
*   [Active] Prefer "Flutter" for mobile.
*   [Active] "Premium" design aesthetic is non-negotiable.
*   **Protocol**: User initiates Mode Switch and Session Close. Agent MUST NOT ask.

## Lessons Learned
*(Agent to append new lessons here when a mistake is made or a correction is received)*


*   **2026-01-19** - Protocol: In Planning Mode, use branch 'main'. Do NOT create new branches until Building Mode.
*   **2026-01-21** - **Jules Integration**: Auto-Discovery should be triggered via backend `after_save` hooks (Frappe), not manual frontend buttons.
*   **2026-01-21** - **Optimization**: Avoid frontend polling (`setInterval`) for Agent status to save quota; use Manual Refresh.
*   **2026-01-21** - **Optimization**: Combine "Context Fetching" and "Initial Ideation" prompts into a single session to reduce overhead.
*   **2026-01-21** - **Environment**: `bench` CLI is unavailable in this environment; verify backend logic via direct Python scripts or API calls.
*   **2026-01-21** - **Protocol**: Upon Session Start/Wakeup, Agent **MUST** check project root for `.cursorrules` to re-ground itself in the protocol. Do not assume context.
