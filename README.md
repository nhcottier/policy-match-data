# Policy Match data

This repository publishes the signed, source-linked policy catalogue used by the independent **Policy Match** iPhone and iPad app.

Only public policy information is hosted here. The app never uploads responses, notes or match results.

## Published feed

- `manifest.json` describes the current release.
- `manifest.sig` is an Ed25519 signature over the exact bytes of `manifest.json`.
- `datasets/<version>.json` contains the policy catalogue.

The app pins the corresponding Ed25519 public key, verifies the manifest signature, verifies the dataset SHA-256 digest and validates the schema before activating an update. If any check fails, the app keeps its last known-good data.

## Publishing an update

1. Generate a reviewed dataset from the authoritative workbook.
2. Add it under `datasets/` without replacing an earlier release.
3. Update `release.json` to point to the new file.
4. Open and review a pull request, then merge it to `main`.

The GitHub Pages workflow validates the dataset, builds the public feed and signs the manifest using a repository secret. The private signing key is never committed.

## Policy identity rules

- Editorial corrections retain the existing policy ID.
- A materially changed commitment receives a new ID.
- Withdrawn and superseded policies remain in the dataset with their lifecycle status so existing responses are not silently reassigned.
- Every policy requires a specific HTTPS source, verification date and status.

Policy Match is independent and is not affiliated with the Electoral Commission or any political party.
