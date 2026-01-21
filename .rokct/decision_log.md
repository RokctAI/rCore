# Architectural Decision Log (ADR)

**Purpose**: Record clear "Subject Closed" decisions to prevent re-debating them.

| ID | Date | Topic | Decision | Status |
| :--- | :--- | :--- | :--- | :--- |
| ADR-001 | 2026-01-17 | Tech Stack | Use Frappe (Backend), Next.js (Frontend), Flutter (Mobile). | **DECIDED** |
| ADR-002 | 2026-01-17 | Design | "Premium" aesthetic with modern typography and animations. | **DECIDED** |
| ADR-003 | 2026-01-21 | Discovery Workflow | Trigger Auto-Discovery via Backend `after_save` hook. Remove manual content scan buttons. | **DECIDED** |
| ADR-004 | 2026-01-21 | Data Usage | Frontend MUST use Manual Refresh for Agent Status. NO Auto-polling (`setInterval`). | **DECIDED** |
| ADR-005 | 2026-01-21 | Jules Prompting | Combined "Context Fetching" and "Initial Ideation" into single session to reduce overhead. | **DECIDED** |
