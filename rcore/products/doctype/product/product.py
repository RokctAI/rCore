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

from frappe.model.document import Document
import frappe


class Product(Document):
    pass


def auto_vectorize_product(doc, method=None):
    """
    Hooks into Item (Product) on_save/after_insert to generate embeddings via Brain.
    """
    # Only vectorize if there is meaningful content
    if not (doc.item_name or doc.description):
        return

    try:
        # Check if Brain is installed and accessible
        from brain.services.llm_service import embed_text

        # Construct context for embedding
        # We want to capture: Name, Group, Description, Shop
        # "Pizza Margherita (Food) - Delicious cheese pizza"
        text = f"{doc.item_name} ({doc.item_group})"
        if doc.description:
            text += f"\n{doc.description}"
        if hasattr(doc, 'shop') and doc.shop:
            text += f"\nShop: {doc.shop}"

        vector = embed_text(text)

        if vector:
            # Direct database set_value to avoid recursive triggers or permission issues
            frappe.db.set_value("Item", doc.name, "embedding", str(vector))
            # We don't commit here, we let the transaction handler do it

    except ImportError:
        # Brain app not installed or service not available
        pass
    except Exception as e:
        # Log but don't break the save
        frappe.log_error(
            f"PaaS: Auto-vectorization failed for {doc.name}: {e}")
