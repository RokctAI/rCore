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
# Tenant context: session.user validation
import frappe
import json
from frappe.utils import cint
from frappe import _
from .utils import _require_admin


def _api_success(data=None, message=""):
    return {
        "status": True,
        "message": message,
        "data": data,
        "timestamp": frappe.utils.now_datetime().isoformat(),
    }


def _api_error(message="", status_code=500):
    frappe.local.response["http_status_code"] = status_code
    return {
        "status": False,
        "message": message,
        "timestamp": frappe.utils.now_datetime().isoformat(),
    }


@frappe.whitelist(allow_guest=True)
def get_mobile_translations(lang: Any=None) -> Any:
    """
    The get_mobile_translations function retrieves translations for a specified language, defaulting to English if no language is provided. It takes one optional parameter, lang, which represents the target language for the translations. The function returns a dictionary containing the translation keys and their corresponding values, along with a success message.
    """
    target_lang = lang or "en"

    translations = frappe.get_all(
        "PaaS Translation",
        filters={"locale": target_lang, "status": 1},
        fields=["key", "value"],
    )

    result = {t["key"]: t["value"] for t in translations}

    return _api_success(result, message="Successfully fetched")


@frappe.whitelist()
def get_translations_paginate(search: Any=None, group: Any=None, locale: Any=None, perPage: Any=10, page: Any=1, **kwargs) -> Any:
    """
    The get_translations_paginate function retrieves a paginated list of translations based on the provided parameters. It accepts several arguments: search, group, locale, perPage, and page. The search parameter is used to filter translations by key or value, the group parameter filters by translation group, and the locale parameter filters by language locale. The perPage argument determines the number of translations to return per page, and the page argument specifies the current page number. The function returns a dictionary containing the total number of translations, the number of translations per page, and a dictionary of translations where each key is a unique translation key and the value is a list of translation details.
    """
    _require_admin()

    per_page = cint(perPage)
    current_page = cint(page)
    start = (current_page - 1) * per_page

    t_translation = frappe.qb.DocType("PaaS Translation")

    # Base query for filtering
    base_query = frappe.qb.from_(t_translation)

    if group:
        base_query = base_query.where(t_translation.group == group)
    if locale:
        base_query = base_query.where(t_translation.locale == locale)
    if search:
        base_query = base_query.where(
            (t_translation.key.like(f"%{search}%"))
            | (t_translation.value.like(f"%{search}%"))
        )

    # Count total distinct keys
    count_query = base_query.select(
        frappe.qb.fn.Count(frappe.qb.fn.Distinct(t_translation.key))
    )
    total_keys = count_query.run()[0][0]

    if total_keys == 0:
        return _api_success(
            {"total": 0, "perPage": per_page, "translations": {}}
        )

    # Get paginated distinct keys
    keys_query = base_query.select(frappe.qb.fn.Distinct(t_translation.key))
    keys_query = (
        keys_query.orderby(t_translation.key, order=frappe.qb.asc)
        .limit(per_page)
        .offset(start)
    )
    paginated_keys = keys_query.run(as_dict=True)

    keys_list = [r.key for r in paginated_keys]

    # Get details for the fetched keys
    details_query = (
        frappe.qb.from_(t_translation)
        .select(
            t_translation.name,
            t_translation.group,
            t_translation.key,
            t_translation.locale,
            t_translation.value,
            t_translation.status,
        )
        .where(t_translation.key.isin(keys_list))
    )

    if search:
        details_query = details_query.where(
            (t_translation.key.like(f"%{search}%"))
            | (t_translation.value.like(f"%{search}%"))
        )
    if group:
        details_query = details_query.where(t_translation.group == group)
    if locale:
        details_query = details_query.where(t_translation.locale == locale)

    details_query = details_query.orderby(
        t_translation.key, order=frappe.qb.asc
    )
    details = details_query.run(as_dict=True)

    grouped = {}
    for t in details:
        k = t["key"]
        if k not in grouped:
            grouped[k] = []

        grouped[k].append(
            {
                "id": t["name"],
                "group": t["group"],
                "locale": t["locale"],
                "value": t["value"],
                "status": t["status"],
            }
        )

    result_dict = {}
    for k in keys_list:
        if k in grouped:
            result_dict[k] = grouped[k]

    return _api_success(
        {"total": total_keys, "perPage": per_page, "translations": result_dict}
    )


@frappe.whitelist()
def create_translation() -> Any:
    """
    The create_translation function is used to create a new translation entry in the database. It requires three parameters: group, key, and value, which are retrieved from the form dictionary. The group parameter specifies the translation group, the key parameter specifies the unique identifier for the translation, and the value parameter is a dictionary containing locale-text pairs. If the value parameter is provided as a string, it is attempted to be parsed as a JSON object. The function first deletes any existing translation with the same key, then creates new translation documents for each locale-text pair in the values dictionary. The function returns a success message if the operation is completed successfully, or an error message with a 400 status code if the parameters are invalid.
    """
    _require_admin()
    data = frappe.form_dict
    group = data.get("group")
    key = data.get("key")
    values = data.get("value")

    if isinstance(values, str):
        try:
            values = json.loads(values)
        except Exception:
            pass

    if not group or not key or not isinstance(values, dict):
        return _api_error("Invalid parameters", 400)

    frappe.db.delete("PaaS Translation", {"key": key})

    for locale, text in values.items():
        doc = frappe.get_doc(
            {
                "doctype": "PaaS Translation",
                "group": group,
                "key": key,
                "locale": locale,
                "value": text,
                "status": 1,
            }
        )
        doc.insert(ignore_permissions=True)

    return _api_success(message="Successfully created")


@frappe.whitelist()
def update_translation(key: Any=None) -> Any:
    """
    The update_translation function is used to update translations for a specific key in the system. It takes an optional key parameter, which defaults to None. If not provided, the function will attempt to retrieve the key from the form data. The function requires administrative privileges and expects the form data to contain a group and a dictionary of values, where each key represents a locale and the corresponding value is the translated text. If the provided values are in string format, the function will attempt to parse them as JSON. The function will delete any existing translations for the target key and then insert new translations based on the provided values. If any required parameters are missing or invalid, the function will return an error response. Otherwise, it will return a success message indicating that the translations have been updated successfully.
    """
    _require_admin()
    data = frappe.form_dict
    target_key = key or data.get("key")

    if not target_key:
        return _api_error("Key is required", 400)

    group = data.get("group")
    values = data.get("value")

    if isinstance(values, str):
        try:
            values = json.loads(values)
        except Exception:
            pass

    if not group or not isinstance(values, dict):
        return _api_error("Invalid parameters", 400)

    frappe.db.delete("PaaS Translation", {"key": target_key})

    for locale, text in values.items():
        doc = frappe.get_doc(
            {
                "doctype": "PaaS Translation",
                "group": group,
                "key": target_key,
                "locale": locale,
                "value": text,
                "status": 1,
            }
        )
        doc.insert(ignore_permissions=True)

    return _api_success(message="Successfully updated")


@frappe.whitelist()
def delete_translation() -> Any:
    """
    The delete_translation function is used to delete translations from the system. It requires administrative privileges to execute. The function takes a single parameter, ids, which is expected to be a list of translation keys to be deleted. If the ids parameter is provided as a string, it is attempted to be parsed as a JSON list. If the ids parameter is invalid or empty, the function returns an error response. Otherwise, it iterates over the provided ids, retrieves the corresponding translation documents, and deletes them, ignoring any permission restrictions. Upon successful deletion, the function returns a success message.
    """
    _require_admin()
    data = frappe.form_dict
    ids = data.get("ids")

    if isinstance(ids, str):
        try:
            ids = json.loads(ids)
        except Exception:
            pass

    if not ids or not isinstance(ids, list):
        return _api_error("Invalid parameters", 400)

    for k in ids:
        docs = frappe.get_all(
            "PaaS Translation", filters={"key": k}, pluck="name"
        )
        for d in docs:
            frappe.delete_doc("PaaS Translation", d, ignore_permissions=True)

    return _api_success(message="Successfully deleted")


def delete_translation_single(key):
    _require_admin()
    if not key:
        return _api_error("Key is required", 400)

    docs = frappe.get_all(
        "PaaS Translation", filters={"key": key}, pluck="name"
    )
    for d in docs:
        frappe.delete_doc("PaaS Translation", d, ignore_permissions=True)

    return _api_success(message="Successfully deleted")


def get_translation_single(key):
    _require_admin()
    if not key:
        return _api_error("Key is required", 400)

    docs = frappe.get_all(
        "PaaS Translation",
        filters={"key": key},
        fields=["name", "group", "key", "locale", "value", "status"],
    )

    if not docs:
        return _api_error("Translation not found", 404)

    data = []
    for t in docs:
        data.append(
            {
                "id": t["name"],
                "group": t["group"],
                "locale": t["locale"],
                "value": t["value"],
                "status": t["status"],
            }
        )

    return _api_success(data)


@frappe.whitelist()
def drop_all_translations() -> Any:
    """
    The drop_all_translations function is used to delete all existing translations in the system. This function requires administrative privileges to execute. It retrieves a list of all translation documents, then iterates over the list to delete each document, ignoring any permission restrictions. Once all translations have been deleted, the function returns a success message indicating that the operation was completed successfully.
    """
    _require_admin()
    docs = frappe.get_all("PaaS Translation", pluck="name")
    for d in docs:
        frappe.delete_doc("PaaS Translation", d, ignore_permissions=True)
    return _api_success(message="Successfully dropped all")


@frappe.whitelist()
def truncate_translations() -> Any:
    """
    The truncate_translations function is used to delete all existing translations in the system. It requires administrative privileges to execute. This function takes no parameters and returns a success message after truncation is complete. The purpose of this function is to reset the translation database, removing all existing records.
    """
    _require_admin()
    frappe.db.delete("PaaS Translation")
    return _api_success(message="Successfully truncated")


@frappe.whitelist()
def restore_all_translations() -> Any:
    """
    restore_all_translations – Restores all deleted PaaS Translation documents. The function first verifies that the caller has administrative privileges, then queries the “Deleted Document” table for entries where the deleted_doctype is “PaaS Translation” and collects their names. It iterates over each name, attempting to restore the document via frappe.model.api.restore_document; any exceptions raised during individual restores are silently ignored. The function takes no parameters and returns a standardized API success response containing the message “Successfully restored”.
    """
    _require_admin()
    deleted = frappe.get_all(
        "Deleted Document",
        filters={"deleted_doctype": "PaaS Translation"},
        pluck="name",
    )
    from frappe.model.api import restore_document

    for d in deleted:
        try:
            restore_document(d)
        except Exception:
            pass
    return _api_success(message="Successfully restored")


@frappe.whitelist()
def import_translations() -> Any:
    """
    The import_translations function is used to import translations from an uploaded file. It requires administrative privileges and expects a file to be uploaded, either in Excel (.xls, .xlsx) or CSV format. The file should contain columns for key, locale, and optionally value and group. The function then iterates over each row in the file, updating existing translations or creating new ones as necessary. If the import is successful, it returns a success message; otherwise, it returns an error message with the reason for the failure.
    """
    _require_admin()
    try:
        import pandas as pd
        import io

        file_data = frappe.request.files.get("file")
        if not file_data:
            return _api_error("No file uploaded", 400)

        content = file_data.stream.read()
        if file_data.filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content))

        for index, row in df.iterrows():
            if "key" not in row or "locale" not in row:
                continue

            existing = frappe.get_all(
                "PaaS Translation",
                filters={"key": row["key"], "locale": row["locale"]},
                pluck="name",
            )
            if existing:
                doc = frappe.get_doc("PaaS Translation", existing[0])
                doc.value = row.get("value", "")
                doc.group = row.get("group", "default")
                doc.save(ignore_permissions=True)
            else:
                frappe.get_doc(
                    {
                        "doctype": "PaaS Translation",
                        "key": row["key"],
                        "locale": row["locale"],
                        "group": row.get("group", "default"),
                        "value": row.get("value", ""),
                        "status": 1,
                    }
                ).insert(ignore_permissions=True)

        return _api_success(message="Successfully imported")

    except Exception as e:
        return _api_error(f"Import failed: {str(e)}")


@frappe.whitelist()
def export_translations() -> Any:
    """
    The export_translations function is used to export all translations from the system into an Excel file. It requires administrative privileges to execute. The function retrieves all translation data, including group, key, locale, and value, and saves it to an Excel file named translations_export.xlsx. If the Excel export fails, it attempts to export the data as a CSV file named translations_export.csv instead. The function returns a success message with the file path and name if the export is successful, or an error message if the export fails.
    """
    _require_admin()
    try:
        import pandas as pd
        from frappe.utils.file_manager import save_file
        import io

        data = frappe.get_all(
            "PaaS Translation", fields=["group", "key", "locale", "value"]
        )
        df = pd.DataFrame(data)

        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df.to_excel(writer, index=False, sheet_name="Translations")
        writer.close()
        output.seek(0)

        fname = "translations_export.xlsx"
        saved = save_file(fname, output.getvalue(), is_private=0)

        return _api_success(
            {"path": saved.file_url, "file_name": fname},
            "Successfully exported",
        )

    except Exception as e:
        try:
            output = io.StringIO()
            df.to_csv(output, index=False)
            fname = "translations_export.csv"
            saved = save_file(
                fname, output.getvalue().encode("utf-8"), is_private=0
            )
            return _api_success(
                {"path": saved.file_url, "file_name": fname},
                "Successfully exported (CSV)",
            )
        except Exception as e2:
            return _api_error(f"Export failed: {str(e2)}")


@frappe.whitelist()
def get_ai_translations() -> Any:
    """
    Get ai translations API endpoint.
    """
    _require_admin()
    data = frappe.form_dict

    model_type = data.get("model_type")
    model_id = data.get("model_id")
    content = data.get("content")
    target_lang = data.get("lang")

    if not content:
        return _api_error("Content is required", 400)

    if not target_lang:
        return _api_error("Target language is required", 400)

    try:
        import requests

        groq_api_key = data.get("api_key")
        if not groq_api_key:
            return _api_error(
                "API key is not configured in the application.", 401
            )

        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
        }

        prompt = f"Translate the following text to {target_lang}. Reply exactly with the translated text only, without quotes or additional explanation:\n\n{content}"

        payload = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15,
        )

        if response.status_code == 200:
            res_json = response.json()
            translated_content = res_json["choices"][0]["message"][
                "content"
            ].strip()

            # Log the translation transaction
            log_doc = frappe.get_doc(
                {
                    "doctype": "PAAS AI Log",
                    "model_type": model_type,
                    "model_id": model_id,
                    "content": content,
                    "translated_text": translated_content,
                    "lang": target_lang,
                }
            )
            # Insert if the doctype exists, otherwise gracefully skip
            if frappe.db.exists("DocType", "PAAS AI Log"):
                log_doc.insert(ignore_permissions=True)

            return _api_success(
                {"title": translated_content},
                message="Successfully translated via Groq AI",
            )
        else:
            return _api_error(f"AI Translation failed: {response.text}", 500)

    except Exception as e:
        return _api_error(f"Translation Error: {str(e)}", 500)
