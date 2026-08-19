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

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class LMSCourse(Document):
    def autoname(self):
        if not self.name:
            self.name = self.generate_slug(self.title)

    def generate_slug(self, title):
        base = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-") or "course"
        slug = base
        counter = 1
        while frappe.db.exists("LMS Course", slug):
            counter += 1
            slug = f"{base}-{counter}"
        return slug

    def validate(self):
        self.validate_published()

    def validate_published(self):
        if self.published and (self.is_new() or self.has_value_changed("published")):
            self.published_on = today()

    def __repr__(self):
        return f"<LMSCourse#{self.name}>"
