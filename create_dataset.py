import json
import polars as pl

# Read raw data
df = pl.read_parquet("data/train-00000-of-00001.parquet").with_row_index(offset=1).rename({"index": "record_id"})

# Write FHIR records to a jsonl file
dicts = df.select("record_id", "fhir").to_dicts()

fhir_records = []
for r in dicts:
    result = r["fhir"]
    fhir_records.append(json.loads(result))

with open("data/fhir.jsonl", "w") as f:
    for record in fhir_records:
        f.write(json.dumps(record) + "\n")

# Write notes to a jsonl file
df.with_columns(
    pl.col("note").str.replace("### Instruction:\n", "")
    .str.replace("### Response:\n", "")
).select("record_id", "note").write_ndjson("data/note.jsonl")
