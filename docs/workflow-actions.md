# Airtable workflow actions

Configure an Airtable project connection with a base ID and personal access token in connection secrets. Give the token access to that base and the read/write record scopes needed by the chosen action. Select that connection in each action. Table names and record IDs belong to that base. Writes run in bounded batches; split larger inputs into calls of at most 10 records.

Action names below match the workflow builder. IDs in parentheses remain compatible with saved workflows. Examples show field values; bind values from earlier steps as needed.

## Choose and configure an action

### List a page of table records (`list_records`)

Read up to 100 Airtable records, optionally matching a formula. Pass the returned offset to another call to read the next page.

```json
{
  "table": "Orders"
}
```

### Read a record by Airtable ID (`get_record`)

Read one record from the selected table using its rec-prefixed Airtable record ID.

```json
{
  "table": "Orders",
  "record_id": "recABCDEFGHIJKLMN"
}
```

### Create new table records (`create_records`)

Create 1–10 records with field values. Airtable assigns their record IDs; use Update or Create or update to change existing records.

```json
{
  "table": "Orders",
  "records": [
    {
      "fields": {
        "Order ID": "order_1042",
        "Status": "Approved"
      }
    }
  ]
}
```

### Update records by Airtable ID (`update_records`)

Patch field values on 1–10 existing records. Each record must include its Airtable ID; omitted fields are preserved.

```json
{
  "table": "Orders",
  "records": [
    {
      "fields": {
        "Order ID": "order_1042",
        "Status": "Approved"
      },
      "id": "recABCDEFGHIJKLMN"
    }
  ]
}
```

### Create or update matching records (`upsert_records`)

Save 1–10 records using their Airtable IDs or 1–3 merge fields to match existing records. Unmatched records are created.

```json
{
  "table": "Orders",
  "records": [
    {
      "fields": {
        "Order ID": "order_1042",
        "Status": "Approved"
      }
    }
  ],
  "merge_fields": [
    "Order ID"
  ]
}
```

### Delete records by Airtable ID (`delete_records`)

Delete 1–10 exact record IDs from the selected table. Supply record IDs returned by a read or create action.

```json
{
  "table": "Orders",
  "record_ids": [
    "recABCDEFGHIJKLMN"
  ]
}
```

## Requirements and result handling

For a new record, supply `records:[{"fields":{"Order ID":"order_1042","Status":"Pending"}}]`. Updates also require each record’s `id`. Upsert records without IDs must include every named merge field. Read `result.records`, `result.count` and `result.offset`; a nonempty offset means another list page is available. Inspect partial-write errors before repeating a batch.

Workflow write actions are suppressed in test mode. Read/search actions still read the configured service. If a write fails after dispatch, inspect the service before repeating it; the write may already have applied.
