import json
import rapidjson


fhir = "./data/fhir.jsonl"

records = []

print("Loading FHIR records from:", fhir)
with open(fhir, "r") as f:
    for line in f:
        # Parse each line as a JSON object
        obj = json.loads(line)
        #parse the inner FHIR string
        record = json.loads(obj["fhir"])
        records.append(record)

print("Total records loaded:", len(records))


print("Saving records to ./data/fhir_records.json")
with open("./data/fhir_records.jsonl", "w") as f:
    f.write(rapidjson.dumps(records, indent=4))


