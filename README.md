# Airtable workflow extension

Connect Airtable tables to Flow Steward workflows for record lookup, data collection and synchronization. Read an individual record by its Airtable ID, or list a table with an optional formula filter. Create new records, patch existing records, merge records using one to three matching fields, and delete records by ID. Actions work directly with the selected base and table, using your existing Airtable record identifiers and field values.

Combine record reads with later workflow steps to look up customer details, collect items for processing or update the status of completed work. Upserts let a workflow match records on business fields instead of looking up every record ID first. Listing returns one page of up to 100 records and an offset for the next request; create, update, upsert and delete actions accept up to ten records per call.

Configure a base and a personal access token with access to it. Field values must already match the Airtable types, since automatic type conversion is not requested. This connector manages table records rather than base schemas and provides no webhooks, triggers or real-time subscriptions.

## Runtime and operation requirements

Standalone Flow Steward host-v2 table CRUD adapter, extension ID `flowsteward.airtable`.
Python 3.12+, standard library plus the host-provided `flowsteward-extension-sdk==0.4.0`. No native drivers or runtime dependency downloads. No triggers, webhooks or realtime subscriptions.

Choose a project connection and pass its ID as `connection_ref`. Account/project context, matching connection type and reference are mandatory. Mutations require a durable `external_effect_id` and are suppressed in test mode before DNS or HTTP. The selected provider credential authorizes direct table access; record IDs and row values are not rewritten with project prefixes.

Only the fixed provider HTTPS origin is reachable. DNS is pinned with SDK 0.4 and every address must be public, including when host private networking is allowed. Redirect handling belongs to the SDK pinned opener. Caller URLs are rejected. Credentials are headers only; provider errors and bodies are not reflected in errors.

Every invocation makes one HTTP attempt within a shared 1–30 second Linux wall-clock deadline. A restored SIGALRM timer bounds DNS, response headers, body reads and decoding; the subprocess runs on its main thread. No retries or automatic page loops. A write dispatched before timeout, malformed/partial response, oversized result or HTTP error reports `timeout_unknown`; inspect provider state before reconciling or retrying. Effect claims do not create provider-side deduplication. Output is capped at 480 KiB. JSON nesting is capped at 16; integers outside ±9007199254740991 must be strings.

## Operations

Connection config: `base_id` (`app` plus 14 alphanumerics), optional `request_timeout_seconds` (default 15). Secret: `personal_access_token`. The PAT needs record read/write access to the selected base.

- `list_records`: table ID/name, optional `page_size` 1–100, opaque `offset`, bounded `filter_by_formula`. Returns exactly one page and next offset.
- `get_record`: table and stable Airtable `record_id`.
- `create_records`, `update_records`, `upsert_records`: 1–10 `{fields}` records; updates require `id`. Upsert takes 1–3 `merge_fields` and every new record contains those fields. Field values follow Airtable types; no implicit typecast.
- `delete_records`: 1–10 unique stable `record_ids`.

Uses fixed `https://api.airtable.com/v0/{base_id}/{table}`. CRUD covers records, not base schema management.

Official API contracts checked 2026-11-01: [list](https://airtable.com/developers/web/api/list-records.md), [create](https://airtable.com/developers/web/api/create-records.md), [update/upsert](https://airtable.com/developers/web/api/update-multiple-records.md), [delete](https://airtable.com/developers/web/api/delete-multiple-records.md). Upsert uses PATCH `performUpsert.fieldsToMergeOn`. HTTP-200 `details.partialSuccess` and permission-redacted write results fail with `partial_write`, a sanitized enum-only `provider_details`, and `timeout_unknown`; the adapter does not silently claim a completed create, update or upsert.

## Verification and release

Tests use mocked pinned HTTP and validate CRUD requests, pagination, input limits, credentials, project context, effect claims, write ambiguity, complete wall-clock deadlines and public DNS enforcement. The canonical Apache-2.0 license bytes are regression checked. No cloud credentials were supplied: live provider behavior is not verified.

From a Flow Steward checkout run `lint.sh --checks extension-static,extension-tests --extension-root <checkout>` in the disposable audit container. Development dependencies install offline from SDK dev wheels plus audit image site packages.

Build `python scripts/package_extension.py --runtime-target linux-amd64` and again with `linux-arm64`. Both deterministic pure Python ZIPs contain `.fs-package.yaml` with only `runtime_target`; `native_executable` is omitted. Source is architecture independent. Archive checksums accompany releases.
