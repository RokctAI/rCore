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

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

"""GitHub-facing roadmap backend.

Restores the GitHub half of the roadmap loop that commit 6fe47e4 removed as
dead code, and replaces the AI half with plain GitHub issues:

* `setup_github_workflow` installs the PR-merged callback workflow into a
  roadmap's source repository via the Contents API.
* `update_task_status_from_pr` is the HMAC-verified endpoint that workflow
  calls back into (through the `rokct.platform.api` ONE-API gateway); it
  matches the feature by the GitHub issue number the dispatcher recorded.
* `assign_to_github` / `_create_github_issue` dispatch a roadmap feature as a
  GitHub issue, so an agent (or a human) working the repository picks it up.

PAT handling follows the `_github_headers()` pattern already live in
`lms/frappe/src/rlms/api/admin.py` (token from `site_config.json`'s
`github_personal_access_token`).
"""

import base64
import hashlib
import hmac
import json
import re
from typing import Any

import frappe
import requests


WORKFLOW_PATH = ".github/workflows/rokct_pr_merged.yml"
GITHUB_API = "https://api.github.com"

# `Roadmap Classification.category` is a Select constrained to exactly these
# three options, so a topic can only be recorded if it maps onto one of them.
# Anything not listed below is skipped rather than guessed: a repository topic
# is free text and is just as likely to be "hacktoberfest" or "open-source" as
# it is to name a platform. `value` is a free Data field, so the topic and
# language names themselves need no whitelist.
_PLATFORM_TOPICS = {
    "android",
    "cross-platform",
    "desktop",
    "ios",
    "ipados",
    "linux",
    "macos",
    "mobile",
    "tvos",
    "watchos",
    "web",
    "windows",
}
_DEPENDENCY_TOPICS = {
    "docker",
    "elasticsearch",
    "kafka",
    "kubernetes",
    "mariadb",
    "mongodb",
    "mysql",
    "nginx",
    "postgres",
    "postgresql",
    "rabbitmq",
    "redis",
    "sqlite",
}
# Languages are ordered by bytes and truncated: GitHub reports every language
# it detects, including a few bytes of stray shell or CSS.
_MAX_LANGUAGES = 5


def _github_headers_or_none():
    """
    Auth headers for the GitHub REST API, or None when no PAT is configured.

    The non-throwing form, for best-effort background work that must leave the
    document saved and the caller undisturbed when the token is absent.
    """
    token = frappe.conf.get("github_personal_access_token")
    if not token:
        return None
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _github_headers():
    """Auth headers for the GitHub REST API, from the site-config PAT."""
    headers = _github_headers_or_none()
    if not headers:
        frappe.throw(
            "GitHub Personal Access Token is not configured in site_config.json."
        )
    return headers


def match_repo(repo_url):
    """
    Split a GitHub repository URL into (owner, repo), or return None if the
    roadmap has no usable repository.

    A Roadmap without a resolvable `source_repository` is an inert board: the
    dispatcher must skip it silently rather than throw or log, so this never
    raises. Callers that genuinely need a repository use `_parse_repo`.
    """
    if not repo_url:
        return None
    match = re.search(
        r"(?:https?://|git@)github\.com[/:](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
        repo_url,
    )
    if not match:
        return None
    return match.group("owner"), match.group("repo")


def fetch_repo_context(repo_url):
    """
    Read what GitHub already knows about a repository: its description, its
    topics, and its language breakdown.

    This is the non-AI replacement for the roadmap enrichment that used to run
    through Jules. Frappe does not hold this data or infer it — it takes it
    from the repo it was given.

    Returns `{"description": str, "classifications": [{"category", "value"}]}`,
    or None when there is nothing to be had: no usable repo URL, no PAT, a
    private or missing repo, or GitHub being unreachable. It never raises, so
    a caller can treat "no enrichment" as an ordinary outcome.
    """
    parsed = match_repo(repo_url)
    if not parsed:
        return None

    headers = _github_headers_or_none()
    if not headers:
        return None

    owner, repo = parsed
    try:
        meta_response = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}", headers=headers, timeout=30
        )
        if meta_response.status_code != 200:
            # 404 for a missing or private repo, 401/403 for a PAT without
            # access. All of them mean the same thing here: no enrichment.
            return None
        meta = meta_response.json() or {}

        languages_response = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/languages",
            headers=headers,
            timeout=30,
        )
        languages = (
            languages_response.json() or {}
            if languages_response.status_code == 200
            else {}
        )
    except (requests.exceptions.RequestException, ValueError):
        # ValueError also covers a non-JSON body (requests' JSONDecodeError).
        return None

    classifications = []
    seen = set()

    def _add(category, value):
        value = str(value or "").strip()
        if value and (category, value) not in seen:
            seen.add((category, value))
            classifications.append({"category": category, "value": value})

    # Language breakdown -> Stack. GitHub returns {language: bytes}; the
    # biggest few are the stack, the tail is stray shell and CSS.
    if isinstance(languages, dict):
        ranked = sorted(
            languages.items(), key=lambda item: item[1] or 0, reverse=True
        )
        for language, _bytes in ranked[:_MAX_LANGUAGES]:
            _add("Stack", language)

    # Topics -> Platform or Dependency, but only the ones we can place in the
    # doctype's Select with confidence. Unrecognised topics are dropped.
    for topic in meta.get("topics") or []:
        normalised = str(topic or "").strip().lower()
        if normalised in _PLATFORM_TOPICS:
            _add("Platform", topic)
        elif normalised in _DEPENDENCY_TOPICS:
            _add("Dependency", topic)

    return {
        "description": (meta.get("description") or "").strip(),
        "classifications": classifications,
    }


def _parse_repo(repo_url):
    """Split a GitHub repository URL into (owner, repo), or throw."""
    parsed = match_repo(repo_url)
    if not parsed:
        frappe.throw("Invalid or unsupported GitHub repository URL format.")
    return parsed


@frappe.whitelist(allow_guest=True)
def update_task_status_from_pr(
    issue_number: Any = None, pull_request_url: Any = None
) -> Any:
    """
    Receives a secure call from our custom GitHub Action to update a task's status.

    The workflow POSTs the ONE-API gateway envelope

        {"cmd": "api.roadmap.update_task_status_from_pr",
         "payload": {"issue_number": <int>, "pull_request_url": "<url>"}}

    to `{site_url}/api/v1/method/rokct.platform.api`; the gateway resolves
    `cmd` through the manifest alias and calls this function with the payload
    keys as kwargs. The request is verified with the HMAC signature the
    workflow computed over the raw request body (i.e. the full envelope).
    """
    # 1. Authenticate the request using HMAC signature
    settings = frappe.get_doc("Roadmap Settings")
    secret = settings.get_password("github_action_secret")
    if not secret:
        frappe.log_error(
            "GitHub Action Secret is not configured in Roadmap Settings.",
            "Webhook Security Error",
        )
        frappe.throw("Authentication failed.", frappe.PermissionError)

    signature_header = frappe.request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        frappe.throw(
            "Authentication failed: Missing X-Hub-Signature-256 header.",
            frappe.PermissionError,
        )

    try:
        signature_type, signature = signature_header.split("=", 1)
    except ValueError:
        frappe.throw(
            "Authentication failed: Invalid signature format.", frappe.PermissionError
        )

    if signature_type != "sha256":
        frappe.throw(
            "Authentication failed: Unsupported signature type.", frappe.PermissionError
        )

    # Calculate the expected signature
    mac = hmac.new(
        secret.encode("utf-8"), msg=frappe.request.data, digestmod=hashlib.sha256
    )
    expected_signature = mac.hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        frappe.throw(
            "Authentication failed: Signature mismatch.", frappe.PermissionError
        )

    # 2. Get the issue identifier. The gateway dispatch passes the envelope's
    #    payload keys in as kwargs; on a direct call, fall back to the raw
    #    request body (unwrapping a gateway envelope if one is present).
    #    Features are dispatched as GitHub issues, so the workflow reports the
    #    issue the merged PR closed.
    if issue_number is None:
        data = json.loads(frappe.request.data)
        if isinstance(data.get("payload"), dict):
            data = data["payload"]
        issue_number = data.get("issue_number")
        if pull_request_url is None:
            pull_request_url = data.get("pull_request_url")
    if not issue_number:
        frappe.throw("issue_number not provided.")

    # 3. Find and update the Roadmap Feature
    feature_doc_name = frappe.db.get_value(
        "Roadmap Feature", {"issue_number": frappe.utils.cint(issue_number)}
    )
    if feature_doc_name:
        feature_doc = frappe.get_doc("Roadmap Feature", feature_doc_name)
        feature_doc.db_set("status", "Done")
        feature_doc.db_set("ai_status", "Merged")

        if pull_request_url:
            feature_doc.db_set("pull_request_url", pull_request_url)

        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Task {feature_doc_name} marked as Done.",
        }
    else:
        return {"status": "not_found", "message": "No matching task found."}


@frappe.whitelist()
def setup_github_workflow(roadmap_name: Any) -> Any:
    """
    Checks if the GitHub workflow file exists in the repository. If not, it
    creates it directly through the GitHub Contents API using the site-config
    PAT.

    This is the fallback route, not the primary one. The Protocol distributes
    the same workflow to the same `WORKFLOW_PATH` in every repository under
    `RokctAI/` on each `initiate` run, so for an in-organisation source
    repository the file is already there and this function only records the
    fact. What it is actually for is a roadmap whose `source_repository` sits
    OUTSIDE the organisation, which no Protocol run ever touches.
    """
    # 1. Get roadmap and GitHub details
    roadmap_doc = frappe.get_doc("Roadmap", roadmap_name)
    repo_url = roadmap_doc.source_repository
    if not repo_url:
        frappe.throw("Roadmap does not have a source repository defined.")

    headers = _github_headers()
    owner, repo = _parse_repo(repo_url)

    # 2. Check if the workflow file already exists.
    # `WORKFLOW_PATH` is deliberately the same path the Protocol distributes
    # to (`workflows/.rok/rokct_pr_merged.yml` -> `.github/workflows/
    # rokct_pr_merged.yml`), so the two routes converge on one file rather than
    # installing two workflows that both report the same merge. For any
    # repository under `RokctAI/` the Protocol has already put the file there,
    # which means this GET returns 200 and the roadmap is marked Linked without
    # a commit. That is the intended outcome, not a near miss: the org-wide
    # copy reads its endpoint and secret from org-level Actions configuration
    # and needs no per-repository step, so overwriting it with a site-templated
    # copy would be a downgrade.
    api_url = (
        f"https://api.github.com/repos/{owner}/{repo}/contents/{WORKFLOW_PATH}"
    )

    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        if response.status_code == 200:
            # Either the Protocol distributed it (in-org) or a previous run of
            # this function committed it (out-of-org). Either way the callback
            # is installed, so the repo is considered linked.
            roadmap_doc.db_set("github_status", "Linked")
            frappe.db.commit()
            return {
                "status": "exists",
                "message": "The GitHub workflow file already exists and the roadmap has been marked as Linked.",
            }
        elif response.status_code != 404:
            frappe.throw(
                f"Failed to check for workflow file. GitHub API responded with status {
                    response.status_code
                }: {response.text}"
            )
    except requests.exceptions.RequestException as e:
        frappe.throw(f"Could not connect to GitHub API: {e}")

    # 3. Build the workflow body from the configured template.
    if frappe.conf.get("app_role") == "control":
        site_url = frappe.conf.get("control_plane_url")
    else:
        db_name = frappe.conf.get("db_name")
        scheme = frappe.conf.get("tenant_site_scheme", "https")
        hostname = db_name.replace("_", ".")
        site_url = f"{scheme}://{hostname}"

    # The workflow calls back through the ONE-API gateway: it POSTs
    #   {"cmd": "api.roadmap.update_task_status_from_pr",
    #    "payload": {"issue_number": <int>, "pull_request_url": "<url>"}}
    # to this URL, signing the raw body with the shared HMAC secret. The
    # gateway resolves `cmd` via the manifest alias and passes the payload
    # keys to `update_task_status_from_pr` as kwargs.
    api_endpoint_url = f"{site_url}/api/v1/method/rokct.platform.api"

    settings = frappe.get_doc("Roadmap Settings")
    workflow_template = settings.github_action_yaml
    if not workflow_template:
        frappe.throw("GitHub Action YAML is not configured in Roadmap Settings.")

    # Populate the template with the dynamic URL
    workflow_content = workflow_template.format(api_endpoint_url=api_endpoint_url)

    # 4. Create the file (the 404 above means it is not there yet, so no sha).
    payload = {
        "message": "feat: Add ROKCT PR-to-task workflow",
        "content": base64.b64encode(workflow_content.encode("utf-8")).decode("ascii"),
    }

    try:
        create_response = requests.put(
            api_url, headers=headers, json=payload, timeout=30
        )
    except requests.exceptions.RequestException as e:
        frappe.throw(f"Could not connect to GitHub API: {e}")

    if create_response.status_code not in (200, 201):
        frappe.throw(
            f"Failed to create the workflow file. GitHub API responded with status {
                create_response.status_code
            }: {create_response.text[:500]}"
        )

    roadmap_doc.db_set("github_status", "Linked")
    frappe.db.commit()

    return {
        "status": "created",
        "path": WORKFLOW_PATH,
        "message": "The ROKCT PR-to-task workflow was committed to the repository and the roadmap has been marked as Linked.",
    }


def _create_github_issue(repo_url, title, body, labels=None):
    """
    Opens an issue on `repo_url` and returns (issue_number, issue_url).
    """
    owner, repo = _parse_repo(repo_url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues"

    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels

    try:
        response = requests.post(
            api_url, headers=_github_headers(), json=payload, timeout=30
        )
    except requests.exceptions.RequestException as e:
        frappe.throw(f"Could not connect to GitHub API: {e}")

    if response.status_code != 201:
        frappe.throw(
            f"Failed to create the GitHub issue. GitHub API responded with status {
                response.status_code
            }: {response.text[:500]}"
        )

    issue = response.json() or {}
    return issue.get("number"), issue.get("html_url")


# --- App-ideas boards -------------------------------------------------------
#
# A Roadmap with `is_app_ideas_board` set points at the factory repository and
# treats its cards as proposals for standalone apps. Dispatching one has to
# produce an issue the factory's spawn flow will accept, which means two
# things and only two things differ from every other roadmap:
#
#   * the body is shaped like the `app-idea` issue form rather than prose, so
#     `.github/scripts/parse_app_idea.py` can read it, and
#   * the issue carries the `app-idea` label, because
#     `.github/workflows/app_spawn.yml` gates on
#     `label.name == 'approved' && contains(labels.*.name, 'app-idea')`.
#
# Applying `approved` by hand is still what mints the repo. Nothing here
# applies it.

APP_IDEA_LABEL = "app-idea"

# Verbatim from `.github/ISSUE_TEMPLATE/app-idea.yml`. The parser normalises
# headings (lowercased, punctuation to spaces) before matching, so it would
# also accept near-misses — but an issue a human opens and an issue this
# dispatcher opens should be the same document, so these stay byte-identical
# to the form's own labels.
APP_IDEA_HEADINGS = (
    "App name",
    "One-line description",
    "Rationale",
    "Visibility",
    "Target owner",
)

# Mirrors SLUG_RE in `.github/scripts/parse_app_idea.py`: lowercase letters,
# digits and hyphens, 2-64 characters, starting and ending alphanumeric.
APP_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")
APP_SLUG_MAX_LENGTH = 64

# `app_spawn.yml` creates the repository with whatever this says. Private is
# the safe half of the choice and matches the issue form's own default: moving
# a card into a build column should never publish a repository as a side
# effect. Flipping a repo to public afterwards is one click; un-publishing an
# idea is not.
APP_IDEA_VISIBILITY = "private"


def _slugify_app_name(text):
    """Reduce `text` to a repository slug, or to "" if nothing survives.

    Lowercases, turns every run of non-alphanumerics into a single hyphen
    (the `+` is what collapses repeats), trims to the length the slug regex
    allows, and strips hyphens off both ends — including any the trim exposed.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug[:APP_SLUG_MAX_LENGTH].strip("-")


def _app_idea_slug(feature_doc):
    """Resolve the repository slug for an app-idea card, or throw.

    The card's optional `app_slug` wins so a title like "Split the till slip
    with your mates" can still become `receipt-splitter`; otherwise the title
    is slugified. Either way the result is validated against the same regex
    the factory parser applies, because the alternative is opening an issue
    that fails in CI with the roadmap none the wiser.
    """
    source = (feature_doc.get("app_slug") or "").strip()
    origin = "App Slug"
    if not source:
        source, origin = (feature_doc.feature or "").strip(), "title"

    slug = _slugify_app_name(source)
    if not APP_SLUG_RE.match(slug):
        got = f'came out as "{slug}"' if slug else "leaves nothing usable"
        frappe.throw(
            f'Cannot dispatch the roadmap card "{feature_doc.feature}" as an '
            f'app idea: its {origin} ("{source}") {got}, which is not a valid '
            "repository slug. Set the card's App Slug field to lowercase "
            "letters, digits and hyphens — 2 to 64 characters, starting and "
            "ending with a letter or digit."
        )
    return slug


def _demote_h3(text):
    """Push any `### ` heading in user text down to `#### `.

    The factory parser splits the body on `^###\\s+`, so a card whose
    explanation happens to start a line that way would silently invent a
    section and swallow everything after it. `####` renders almost the same
    and cannot match `^###[ \\t]+`.
    """
    return re.sub(r"(?m)^###([ \t])", r"####\1", text or "")


def _app_idea_rationale(roadmap, feature_doc):
    """The build brief for one app idea.

    `parse_app_idea.py` renames this to `spec` and the spawn flow copies it
    verbatim into the new repository's `docs/spec.md`, so it carries the
    card's explanation plus the same board context the prose body reports —
    tags, the roadmap's stack/platform/dependency classifications, and which
    roadmap it came from. That is the only description of the app the agent
    building it will ever see.
    """
    explanation = _demote_h3(feature_doc.explanation or "").strip()
    if not explanation:
        frappe.throw(
            f'Cannot dispatch the roadmap card "{feature_doc.feature}" as an '
            "app idea: its Explanation is empty, and that text is what becomes "
            "the new repository's build spec. Describe what the app does, who "
            "it is for and what done looks like, then move the card again."
        )

    lines = [explanation, ""]

    tags = [t.tag for t in (feature_doc.get("tags") or []) if t.tag]
    if tags:
        lines.append(f"**Categories:** {', '.join(tags)}")

    classifications = roadmap.get("classifications") or []
    for category in ("Stack", "Platform", "Dependency"):
        values = [c.value for c in classifications if c.category == category]
        if values:
            lines.append(f"**{category}:** {', '.join(values)}")

    if roadmap.description:
        lines.append("")
        lines.append(f"**Roadmap:** {roadmap.title} — {roadmap.description}")
    else:
        lines.append("")
        lines.append(f"**Roadmap:** {roadmap.title}")

    return "\n".join(lines).strip()


def _app_idea_issue_body(roadmap, feature_doc):
    """Issue body in the shape GitHub renders the `app-idea` form into.

    Field order, headings and the blank line between a heading and its value
    all follow what GitHub produces for a submitted issue form, so the result
    is indistinguishable from one Ray filled in by hand.
    """
    # The board points at the factory; new app repos land under the same owner
    # unless the parser's own default takes over. `_parse_repo` throws on an
    # unusable URL, but `assign_to_github` has already established the URL
    # parses before it gets here.
    owner, _repo = _parse_repo(roadmap.source_repository)

    values = {
        "App name": _app_idea_slug(feature_doc),
        "One-line description": _demote_h3(
            (feature_doc.feature or "").strip()
        ),
        "Rationale": _app_idea_rationale(roadmap, feature_doc),
        "Visibility": APP_IDEA_VISIBILITY,
        "Target owner": owner,
    }
    return (
        "\n\n".join(
            f"### {heading}\n\n{values[heading]}" for heading in APP_IDEA_HEADINGS
        )
        + "\n"
    )


def _feature_issue_body(roadmap, feature_doc):
    """Plain-text issue body describing one roadmap feature."""
    lines = [feature_doc.explanation or "No details provided.", ""]

    tags = [t.tag for t in (feature_doc.get("tags") or []) if t.tag]
    if tags:
        lines.append(f"**Categories:** {', '.join(tags)}")

    classifications = roadmap.get("classifications") or []
    for category in ("Stack", "Platform", "Dependency"):
        values = [c.value for c in classifications if c.category == category]
        if values:
            lines.append(f"**{category}:** {', '.join(values)}")

    if roadmap.description:
        lines.append("")
        lines.append(f"**Roadmap:** {roadmap.title} — {roadmap.description}")
    else:
        lines.append("")
        lines.append(f"**Roadmap:** {roadmap.title}")

    lines.append("")
    lines.append(
        "_Opened automatically from the ROKCT roadmap. Closing the pull request "
        "that resolves this issue moves the roadmap feature to Done._"
    )
    return "\n".join(lines)


@frappe.whitelist()
def assign_to_github(docname: Any) -> Any:
    """
    Dispatches a Roadmap Feature to its roadmap's source repository as a GitHub
    issue, and records the issue on the feature so the PR-merged webhook can
    match it back.

    A Roadmap with no usable `source_repository` is an inert board: this
    returns a skip without throwing, logging, or writing anything, so moving a
    feature around such a board has no side effect at all.
    """
    feature_doc = frappe.get_doc("Roadmap Feature", docname)
    roadmap = frappe.get_doc("Roadmap", feature_doc.parent)

    if not match_repo(roadmap.source_repository):
        return {
            "status": "skipped",
            "reason": "no_source_repository",
        }

    # Never open a second issue for a feature that already has one. The sweep
    # filters on `issue_number is not set` as well, so this is the backstop for
    # a race or a direct call: a card dragged out of the build column and back
    # in keeps its issue_number and is simply skipped, not re-dispatched.
    if feature_doc.issue_number:
        return {
            "status": "skipped",
            "reason": "already_dispatched",
            "issue_number": feature_doc.issue_number,
            "issue_url": feature_doc.issue_url,
        }

    # An app-ideas board is the only thing that changes the shape of the
    # issue. Every other roadmap keeps the prose body and the
    # enhancement/bug label it has always had.
    if roadmap.get("is_app_ideas_board"):
        title = f"[app] {feature_doc.feature}"
        body = _app_idea_issue_body(roadmap, feature_doc)
        labels = [APP_IDEA_LABEL]
    else:
        title = feature_doc.feature
        body = _feature_issue_body(roadmap, feature_doc)
        labels = ["bug"] if feature_doc.type == "Bug" else ["enhancement"]

    issue_number, issue_url = _create_github_issue(
        roadmap.source_repository,
        title,
        body,
        labels=labels,
    )

    if not issue_number:
        frappe.throw("GitHub did not return an issue number.")

    # Same transitions the Jules dispatcher used.
    feature_doc.db_set("status", "Doing")
    feature_doc.db_set("ai_status", "Assigned")
    feature_doc.db_set("issue_number", issue_number)
    feature_doc.db_set("issue_url", issue_url)
    frappe.db.commit()

    return {"issue_number": issue_number, "issue_url": issue_url}
