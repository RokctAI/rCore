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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from rcore.agent.roadmap.api import match_repo


class Roadmap(Document):
    def before_save(self):
        """
        On saving the Roadmap document, update the dispatch and GitHub
        statuses from the current configuration.

        A Roadmap is "Ready" when it points at a repository we can open issues
        on. This used to mean "a Jules API key is configured" — it no longer
        does, because the platform does not hold or use an AI key on a user's
        behalf. No repository means an inert board: features can be moved
        around it and nothing happens.
        """
        if match_repo(self.source_repository):
            self.ai_status = "Ready"
        else:
            self.ai_status = "Not Configured"
            self.github_status = "Unlinked"

    def after_save(self):
        """
        Fill in what the repository already tells us, in the background.

        This used to read `jules_api_key` and enqueue `discover_roadmap_context`,
        so saving a Roadmap made the platform call Jules on the platform's key.
        The trigger and the fields it fills are unchanged; the source is not.
        `enrich_roadmap_from_repo` reads the repository's own description,
        topics and language breakdown over the GitHub API — no AI service and
        no AI key. `discover_roadmap_context` stays in the codebase, but
        nothing triggers it.

        Enqueued rather than run inline, so a slow or unreachable GitHub never
        holds up the save. Skipped entirely for a repo-less roadmap, and once
        both fields are populated — including when a human populated them.
        """
        if not match_repo(self.source_repository):
            return

        if self.description and self.classifications:
            return

        frappe.enqueue(
            "rcore.agent.roadmap.tasks.enrich_roadmap_from_repo",
            roadmap_name=self.name,
        )
