"""Fail-closed editorial gate. News is discovery, not publication evidence."""

from datetime import date
from urllib.parse import urlparse


PARTY_HOSTS = {
    "National": "www.national.org.nz",
    "Labour": "www.labour.org.nz",
    "Green Party": "www.greens.org.nz",
    "ACT": "www.act.org.nz",
    "New Zealand First": "www.nzfirst.nz",
    "Te Pāti Māori": "www.maoriparty.org.nz",
    "Opportunity Party": "www.opportunity.org.nz",
}


def apply_reviews(policies, review_document):
    """Require an explicit review of the exact input; never approve by domain alone.

    The review document is editorial source, not downloaded content. Changes to
    any imported public field invalidate its prior confirmation. Held records
    stay in this source document and are never emitted to the app.
    """
    if review_document.get("schemaVersion") != 1:
        raise ValueError("Unsupported editorial review schema")
    reviews = review_document["reviews"]
    by_id = {r["input"]["id"]: r for r in reviews}
    ids = {p["id"] for p in policies}
    if len(ids) != len(policies) or len(by_id) != len(reviews):
        raise ValueError("Duplicate policy or review ID")
    if ids != set(by_id):
        raise ValueError("Every input policy must have exactly one editorial review")
    published, retired = [], []
    for policy in policies:
        review = by_id[policy["id"]]
        if review["input"] != policy:
            raise ValueError(f"Changed input needs fresh verification: {policy['id']}")
        if not review.get("reason", "").strip():
            raise ValueError("A review reason is required")
        if review["decision"] == "hold":
            retired.append(policy["id"])
            continue
        if review["decision"] != "confirmed":
            raise ValueError("Publication requires official confirmation")
        checked = date.fromisoformat(review["verifiedAt"])
        if checked > date.today():
            raise ValueError("Verification date cannot be in the future")
        source = review["officialSourceURL"]
        parsed = urlparse(source)
        if (parsed.scheme != "https" or parsed.netloc != PARTY_HOSTS.get(policy["party"])
                or parsed.path in ("", "/") or any(c.isspace() for c in source)):
            raise ValueError(f"Expected a direct official party source: {policy['id']}")
        updates = review.get("updates", {})
        if set(updates) - {"title", "summary", "topic"}:
            raise ValueError("Review updates may only change title, summary and topic")
        if any(not isinstance(v, str) or not v.strip() for v in updates.values()):
            raise ValueError("Reviewed text must not be empty")
        result = dict(policy, **updates)
        result["sourceURL"] = source
        result["dateAnnouncedOrVerified"] = review["verifiedAt"]
        replacement = review.get("replacementID")
        if replacement:
            if not isinstance(replacement, str) or not replacement.startswith("nzpt-") or replacement in ids:
                raise ValueError("Replacement must have a new stable policy ID")
            result["id"] = replacement
            result["supersedesPolicyID"] = policy["id"]
            retired.append(policy["id"])
        published.append(result)
    if not published or len({p['id'] for p in published}) != len(published):
        raise ValueError("Empty publication or duplicate output IDs")
    return published, retired
