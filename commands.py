"""Airtable record API contract; one explicit page or bounded batch."""

import re
from urllib.parse import quote, urlencode
from validation import Failure, require, text, integer


def record_id(value):
    require(re.fullmatch(r"rec[A-Za-z0-9]{14}", text(value)), "Invalid record ID.")
    return value


def prepare(name, args, config):
    fields = {
        "list_records": {"page_size", "offset", "filter_by_formula"},
        "get_record": {"record_id"},
        "create_records": {"records"},
        "update_records": {"records"},
        "upsert_records": {"records", "merge_fields"},
        "delete_records": {"record_ids"},
    }
    require(name in fields, "Unknown action.")
    require(set(args) <= fields[name] | {"table", "connection_ref"}, "Unknown input field.")
    table = text(args.get("table"))
    require(table not in {".", ".."}, "Invalid table.")
    path = "/v0/" + config["base_id"] + "/" + quote(table, safe="")
    query = []
    body = None
    method = "GET"
    expected: object = None
    if name == "list_records":
        query.append(("pageSize", integer(args.get("page_size", 100), 1, 100)))
        if "offset" in args:
            query.append(("offset", text(args["offset"], 4096)))
        if "filter_by_formula" in args:
            query.append(("filterByFormula", text(args["filter_by_formula"], 8192)))
    elif name == "get_record":
        path += "/" + record_id(args.get("record_id"))
    elif name == "delete_records":
        ids = args.get("record_ids")
        require(isinstance(ids, list) and 1 <= len(ids) <= 10, "Delete requires 1 to 10 IDs.")
        require(len(set(ids)) == len(ids), "Duplicate record IDs.")
        query = [("records[]", record_id(v)) for v in ids]
        method = "DELETE"
        expected = set(ids)
    else:
        records = args.get("records")
        require(isinstance(records, list) and 1 <= len(records) <= 10, "Requires 1 to 10 records.")
        for row in records:
            require(
                isinstance(row, dict)
                and set(row) <= {"id", "fields"}
                and isinstance(row.get("fields"), dict)
                and bool(row["fields"]),
                "Each record requires nonempty fields.",
            )
            require(
                all(isinstance(k, str) and 0 < len(k.encode()) <= 256 for k in row["fields"]),
                "Invalid field name.",
            )
            if "id" in row:
                record_id(row["id"])
            if name == "update_records":
                record_id(row.get("id"))
            if name == "create_records":
                require("id" not in row, "Create IDs are assigned by Airtable.")
        ids = [r["id"] for r in records if "id" in r]
        require(len(ids) == len(set(ids)), "Duplicate record IDs.")
        body = {"records": records}
        method = "POST" if name == "create_records" else "PATCH"
        expected = len(records)
        if name == "upsert_records":
            merge = args.get("merge_fields")
            require(
                isinstance(merge, list) and 1 <= len(merge) <= 3, "Requires 1 to 3 merge fields."
            )
            for field in merge:
                text(field, 256)
            require(len(set(merge)) == len(merge), "Duplicate merge fields.")
            for row in records:
                require(
                    "id" in row or all(f in row["fields"] for f in merge),
                    "Merge fields must be present.",
                )
            body["performUpsert"] = {"fieldsToMergeOn": merge}
    if query:
        path += "?" + urlencode(query)
    return method, path, body, expected


def result(name, value, expected):
    require(isinstance(value, dict), "Invalid provider envelope.", code="invalid_provider_response")
    if name in {"create_records", "update_records", "upsert_records"} and "details" in value:
        details = value["details"]
        require(
            isinstance(details, dict)
            and details.get("message") in {"partialSuccess", "cellsRedactedDueToLimitedPermissions"}
            and isinstance(details.get("reasons"), list),
            "Invalid provider write details.",
            code="invalid_provider_response",
        )
        allowed = {
            "attachmentsFailedUploading",
            "attachmentUploadRateIsTooHigh",
            "restrictedPermissions",
        }
        reasons = list(
            dict.fromkeys(
                reason
                for reason in details["reasons"]
                if isinstance(reason, str) and reason in allowed
            )
        )
        failure = Failure(
            "partial_write", "Provider reported a partial or permission-redacted write."
        )
        failure.details = {"message": details["message"], "reasons": reasons}
        raise failure
    rows = [value] if name == "get_record" else value.get("records")
    require(
        isinstance(rows, list) and len(rows) <= 100,
        "Invalid provider records.",
        code="invalid_provider_response",
    )
    require(
        all(
            isinstance(r, dict)
            and isinstance(r.get("id"), str)
            and (
                r.get("deleted") is True
                if name == "delete_records"
                else isinstance(r.get("fields"), dict)
            )
            for r in rows
        ),
        "Invalid record result.",
        code="invalid_provider_response",
    )
    if isinstance(expected, int):
        require(len(rows) == expected, "Incomplete batch result.", code="invalid_provider_response")
    if isinstance(expected, set):
        require(
            {r["id"] for r in rows} == expected and len(rows) == len(expected),
            "Incomplete delete result.",
            code="invalid_provider_response",
        )
    offset = value.get("offset", "")
    require(
        isinstance(offset, str) and len(offset.encode()) <= 4096,
        "Invalid pagination cursor.",
        code="invalid_provider_response",
    )
    return {"records": rows, "count": len(rows), "offset": offset}
