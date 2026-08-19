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

# Re-export this package's whitelisted API functions so the composed app's
# manifest.json whitelisted_methods targets ("rcore.<module>.api.<pkg>.<fn>")
# resolve: frappe.get_attr() imports the package and getattr()s the function
# name, which only works when the function is bound here in __init__.py.
from .admin_content import (  # noqa: F401
    create_admin_banner,
    create_admin_faq,
    create_admin_faq_category,
    delete_admin_banner,
    delete_admin_faq,
    delete_admin_faq_category,
    get_admin_banners,
    get_admin_faq_categories,
    get_admin_faqs,
    get_admin_stories,
    update_admin_banner,
    update_admin_faq,
    update_admin_faq_category,
)
