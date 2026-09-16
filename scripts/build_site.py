#!/usr/bin/env python3
"""Validate a Policy Match dataset and build the unsigned GitHub Pages payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from policy_review import apply_reviews


REQUIRED_POLICY_FIELDS = {
    "id",
    "party",
    "topic",
    "title",
    "summary",
    "sourceURL",
    "dateAnnouncedOrVerified",
    "policyStatus",
    "lifecycleStatus",
    "supersedesPolicyID",
    "supersededByPolicyID",
}
POLICY_STATUSES = {"confirmed2026", "standingCurrent"}
LIFECYCLE_STATUSES = {"active", "withdrawn", "superseded"}


def validate_date(value: object, label: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a date string")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError(f"{label} must use YYYY-MM-DD") from error


def validate_dataset(data: bytes) -> dict[str, object]:
    payload = json.loads(data)
    if payload.get("schemaVersion") != 1:
        raise ValueError("schemaVersion must be 1")
    version = payload.get("datasetVersion")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("datasetVersion is required")
    validate_date(payload.get("dataLastUpdated"), "dataLastUpdated")

    policies = payload.get("policies")
    if not isinstance(policies, list) or not policies:
        raise ValueError("policies must be a non-empty array")

    ids: set[str] = set()
    for index, policy in enumerate(policies):
        if not isinstance(policy, dict):
            raise ValueError(f"policy {index} must be an object")
        missing = REQUIRED_POLICY_FIELDS.difference(policy)
        if missing:
            raise ValueError(f"policy {index} is missing {sorted(missing)}")
        policy_id = policy["id"]
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise ValueError(f"policy {index} has an invalid ID")
        if policy_id in ids:
            raise ValueError(f"duplicate policy ID: {policy_id}")
        ids.add(policy_id)
        for field in ("party", "topic", "title", "summary"):
            if not isinstance(policy[field], str) or not policy[field].strip():
                raise ValueError(f"{policy_id}: {field} is required")
        source = urlparse(str(policy["sourceURL"]))
        if source.scheme != "https" or not source.netloc:
            raise ValueError(f"{policy_id}: sourceURL must use HTTPS")
        validate_date(policy["dateAnnouncedOrVerified"], f"{policy_id}: dateAnnouncedOrVerified")
        if policy["policyStatus"] not in POLICY_STATUSES:
            raise ValueError(f"{policy_id}: invalid policyStatus")
        if policy["lifecycleStatus"] not in LIFECYCLE_STATUSES:
            raise ValueError(f"{policy_id}: invalid lifecycleStatus")

    retired = payload.get("retiredPolicyIDs", [])
    if (not isinstance(retired, list) or any(not isinstance(item, str) or not item for item in retired)
            or len(retired) != len(set(retired)) or ids.intersection(retired)):
        raise ValueError("retiredPolicyIDs must contain unique non-current IDs")
    for policy in policies:
        for field in ("supersedesPolicyID", "supersededByPolicyID"):
            linked_id = policy[field]
            allowed_ids = ids | set(retired) if field == "supersedesPolicyID" else ids
            if linked_id is not None and linked_id not in allowed_ids:
                raise ValueError(f"{policy['id']}: {field} refers to unknown ID {linked_id}")

    return payload


def validate_reviews(dataset, reviews):
    approved, retired = apply_reviews([review["input"] for review in reviews["reviews"]], reviews)
    if dataset["policies"] != approved or dataset.get("retiredPolicyIDs", []) != retired:
        raise ValueError("Dataset must exactly match the officially confirmed editorial reviews")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, default=Path("release.json"))
    parser.add_argument("--output", type=Path, default=Path("site"))
    args = parser.parse_args()

    release = json.loads(args.release.read_text(encoding="utf-8"))
    dataset_path = Path(release["dataset"])
    base_url = str(release["baseURL"]).rstrip("/")
    dataset_data = dataset_path.read_bytes()
    dataset = validate_dataset(dataset_data)
    reviews = json.loads(Path(release["reviews"]).read_text(encoding="utf-8"))
    validate_reviews(dataset, reviews)

    output_dataset = args.output / "datasets" / dataset_path.name
    output_dataset.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(dataset_path, output_dataset)

    manifest = {
        "schemaVersion": 1,
        "datasetSchemaVersion": dataset["schemaVersion"],
        "datasetVersion": dataset["datasetVersion"],
        "publishedAt": dataset["generatedAt"],
        "dataLastUpdated": dataset["dataLastUpdated"],
        "datasetURL": f"{base_url}/datasets/{dataset_path.name}",
        "datasetSHA256": hashlib.sha256(dataset_data).hexdigest(),
        "policyCount": len(dataset["policies"]),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_data = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    (args.output / "manifest.json").write_text(manifest_data, encoding="utf-8")
    (args.output / "index.html").write_text(
        "<!doctype html><meta charset=\"utf-8\"><title>Policy Match data</title>"
        "<main><h1>Policy Match data</h1><p>Signed, source-linked policy updates for the independent Policy Match app.</p></main>\n",
        encoding="utf-8",
    )
    print(f"Validated {manifest['policyCount']} policies")
    print(f"Built dataset {manifest['datasetVersion']}")


if __name__ == "__main__":
    main()
