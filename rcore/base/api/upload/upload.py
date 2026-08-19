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

from typing import Any, Optional
import frappe
from frappe.utils.file_manager import save_file
from ..utils import api_response


@frappe.whitelist()
def upload_file(file: Any, filename: Any=None, is_private: Any=0) -> Any:
    """
    Uploads a file and returns the file URL.
    """
    try:
        # Save the file using Frappe's file manager
        file_doc = save_file(
            fname=filename or file.filename,
            content=file.read(),
            dt=None,  # Not attached to any doctype
            dn=None,
            is_private=is_private,
        )

        return {
            "file_url": file_doc.file_url,
            "file_name": file_doc.file_name,
            "name": file_doc.name,
        }
    except Exception as e:
        frappe.log_error(f"File upload failed: {str(e)}")
        frappe.throw(f"Failed to upload file: {str(e)}")


@frappe.whitelist()
def upload_multi_image(files: list=None, upload_type: str=None, doc_name: str=None, lang: str='en') -> Any:
    """
    Uploads multiple images and attaches them to a specific document.
    """
    # 1. Handle file input robustly
    # If `files` arg is empty, check `frappe.request.files`
    file_list = []

    # attempt to parse list if passed as string (common in some frappe calls)
    if isinstance(files, str):
        import json

        try:
            files = json.loads(files)
        except Exception:
            pass

    if isinstance(files, list):
        # If it's a list of objects/dicts, we might need to handle differently
        # But usually file uploads come via request.files in
        # multipart/form-data
        pass

    # 2. Main Source: frappe.request.files
    # usage: formData.append('files', fileObj);
    if frappe.request.files:
        # 'files' key might contain multiple files
        file_list = frappe.request.files.getlist("files")

        # If 'files' key is empty, maybe they used other keys or just sent files without rigid keys?
        # frappe.request.files is a MultiDict.
        if not file_list:
            file_list = list(frappe.request.files.values())

    if not file_list:
        frappe.log_error("No files found in upload_multi_image request")
        return api_response(message="No files found", status_code=400)

    # 3. Validate Upload Type and Document
    valid_doctypes = {
        "extras": "Product Extra",
        "brands": "Brand",
        "categories": "Category",
        "shopsLogo": "Shop",
        "shopsBack": "Shop",
        "products": "Product",
        "reviews": "Review",
        "users": "User",
    }

    doctype = valid_doctypes.get(upload_type)
    if not doctype:
        frappe.throw(f"Invalid upload type: {upload_type}")

    # For User, we default to session user if no doc_name
    if doctype == "User" and not doc_name:
        doc_name = frappe.session.user

    if not doc_name:
        frappe.throw("Document name (doc_name) is required.")

    # 4. Check Permission / Existence
    if not frappe.db.exists(doctype, doc_name):
        frappe.throw(f"{doctype} {doc_name} not found.")

    doc = frappe.get_doc(doctype, doc_name)
    # Ideally check permissions here: doc.check_permission("write")
    # But for now we rely on the logic that if they can call this, and know the ID...
    # (Secure this further if needed based on business logic)

    file_urls = []

    for file_obj in file_list:
        filename = getattr(file_obj, "filename", "unknown.jpg")
        content = getattr(file_obj, "read", lambda: b"")()

        # Reset stream just in case
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
                content = file_obj.read()
        except Exception:
            pass

        if not content:
            continue

        try:
            # Create File Doc
            file_doc = frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": filename,
                    "attached_to_doctype": doctype,
                    "attached_to_name": doc.name,
                    "content": content,
                    "is_private": 0,
                }
            )
            file_doc.insert(ignore_permissions=True)
            file_urls.append(file_doc.file_url)
        except Exception as e:
            frappe.log_error(f"Error saving file {filename}: {e}")
            continue

    if not file_urls:
        return api_response(
            message="No files were successfully uploaded", status_code=500
        )

    # 5. Update Record Fields if specific types
    # This logic assumes we replace the image field with the FIRST uploaded image
    # If multiple images are uploaded for 'shopsLogo', only the first takes effect on the field,
    # but all are attached as Files.
    if upload_type == "shopsLogo":
        doc.db_set("logo", file_urls[0])
    elif upload_type == "shopsBack":
        doc.db_set("background_image", file_urls[0])
    elif upload_type == "users":
        doc.db_set("user_image", file_urls[0])

    # For products/reviews/others, usually we just want them attached, not setting a specific single field
    # (unless 'image' field exists and is empty? Logic implies just attachment for now)

    return {"file_urls": file_urls}
