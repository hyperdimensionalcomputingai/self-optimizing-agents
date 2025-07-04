import argparse
import json
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Dict, List, Optional


@dataclass
class NameComparison:
    """Represents a name comparison between results and gold standard"""

    family_match: bool
    given_match: bool
    prefix_match: bool
    overall_match: bool
    record_id: int  # Store the record ID for failed matches


@dataclass
class AddressComparison:
    """Represents an address comparison between results and gold standard"""

    line_match: bool
    city_match: bool
    state_match: bool
    postal_code_match: bool
    country_match: bool
    overall_match: bool
    record_id: int  # Store the record ID for failed matches


@dataclass
class SimpleFieldComparison:
    """Represents simple field comparisons between results and gold standard"""

    gender_match: bool
    birth_date_match: bool
    marital_status_match: bool
    overall_match: bool
    record_id: int  # Store the record ID for failed matches


# --- Utility Functions ---
def get_first(arr):
    if isinstance(arr, list) and arr:
        return arr[0]
    return None


def normalize_str(val):
    if val is None:
        return None
    if isinstance(val, list):
        return get_first(val)
    return str(val)


def compare_strict(a, b):
    return a == b


def compare_case_insensitive(a, b):
    if a is None or b is None:
        return a == b
    return str(a).lower() == str(b).lower()


def compare_substring(a, b):
    if a is None or b is None:
        return a == b
    a, b = str(a).lower(), str(b).lower()
    return a in b or b in a


def normalize_fhir_name(fhir_name_array):
    name = get_first(fhir_name_array) or {}
    return {
        "family": name.get("family"),
        "given": name.get("given", []),
        "prefix": get_first(name.get("prefix", [])),
    }


def normalize_fhir_address(fhir_address_array):
    address = get_first(fhir_address_array) or {}
    return {
        "line": get_first(address.get("line", [])),
        "city": address.get("city"),
        "state": address.get("state"),
        "postalCode": address.get("postalCode"),
        "country": address.get("country"),
    }


def normalize_fhir_marital_status(fhir_marital_status):
    if not fhir_marital_status:
        return None
    text = fhir_marital_status.get("text")
    if text:
        return text.replace(" ", "")
    coding = fhir_marital_status.get("coding", [])
    if coding:
        return coding[0].get("display", "").replace(" ", "")
    return None


def combine_practitioner_name(practitioner_data: Dict[str, Any]) -> str:
    """Combine prefix, given, and family names from practitioner data"""
    if not practitioner_data or not isinstance(practitioner_data.get("name"), dict):
        return ""

    name = practitioner_data["name"]
    prefix = name.get("prefix", [])
    given = name.get("given", [])
    family = name.get("family")

    # Handle prefix as array (FHIR standard)
    if prefix and isinstance(prefix, list):
        prefix = get_first(prefix)

    # Handle given as array (FHIR standard)
    if given and isinstance(given, list):
        given = given  # Keep as list to extend later
    elif given and not isinstance(given, list):
        given = [given]
    else:
        given = []

    # Build the full name
    parts = []
    if prefix:
        parts.append(prefix)
    if given:
        parts.extend(given)
    if family:
        parts.append(family)

    return " ".join(parts).strip()


# --- Generalized Evaluation ---
def parse_fhir_bundle(fhir_json_str: str) -> Dict[str, Any]:
    if isinstance(fhir_json_str, dict):
        return fhir_json_str
    return json.loads(fhir_json_str)


def extract_patient_from_bundle(bundle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if bundle.get("resourceType") != "Bundle":
        return None
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            return resource
    return None


def extract_allergy_count_from_bundle(bundle: Dict[str, Any]) -> int:
    """Extract count of AllergyIntolerance resources from FHIR bundle"""
    if bundle.get("resourceType") != "Bundle":
        return 0

    count = 0
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "AllergyIntolerance":
            count += 1
    return count


def extract_immunization_count_from_bundle(bundle: Dict[str, Any]) -> int:
    """Extract count of Immunization resources from FHIR bundle"""
    if bundle.get("resourceType") != "Bundle":
        return 0

    count = 0
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Immunization":
            count += 1
    return count


def extract_immunization_status_from_bundle(bundle: Dict[str, Any]) -> List[str]:
    """Extract status of all Immunization resources from FHIR bundle"""
    if bundle.get("resourceType") != "Bundle":
        return []

    statuses = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Immunization":
            status = resource.get("status")
            if status:
                statuses.append(status)
    return statuses


def extract_immunization_dates_from_bundle(bundle: Dict[str, Any]) -> List[str]:
    """Extract occurrenceDateTime of all Immunization resources from FHIR bundle"""
    if bundle.get("resourceType") != "Bundle":
        return []

    dates = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Immunization":
            # Check both occurrenceDateTime and occurrenceString
            date_time = resource.get("occurrenceDateTime")
            date_string = resource.get("occurrenceString")

            if date_time:
                dates.append(date_time)
            elif date_string:
                dates.append(date_string)
    return dates


def extract_all_practitioners_from_bundle(bundle: Dict[str, Any]) -> list:
    practitioners = set()
    if bundle.get("resourceType") != "Bundle":
        return list(practitioners)

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Encounter":
            participants = resource.get("participant", []) or []
            for participant in participants:
                individual = participant.get("individual", {})
                display = individual.get("display", "")
                if display:
                    practitioners.add(display)

    # Practitioner resources as before
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Practitioner":
            name_array = resource.get("name", [])
            if name_array:
                # Handle name as array (FHIR standard) - take the first name
                name = get_first(name_array)
                if name:
                    combined = combine_practitioner_name({"name": name})
                    if combined:
                        practitioners.add(combined)
    # print("DEBUG: Practitioners:", list(practitioners))
    return list(practitioners)


def read_n_lines(file_path: str, n: int) -> list:
    """Read up to n lines from a file and return as a list."""
    lines = []
    with open(file_path, "r") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            lines.append(line)
    return lines


def evaluate_fields(
    eval_file_path: str, results_file_path: str, field_map: Dict[str, Dict[str, Any]]
):
    """
    field_map: {
        field_name: {
            'extract_fhir': Callable[[Dict], Any],
            'extract_result': Callable[[Dict], Any],
            'compare': Callable[[Any, Any], bool]
        }
    }
    """
    stats = {k: 0 for k in field_map}
    total = 0
    failed_records = {k: [] for k in field_map}
    total_field_comparisons = 0
    total_failed_comparisons = 0
    with open(results_file_path, "r") as results_file:
        results_lines = list(results_file)
    eval_lines = read_n_lines(eval_file_path, len(results_lines))
    for line_num, (eval_line, results_line) in enumerate(zip(eval_lines, results_lines), 1):
        eval_data = json.loads(eval_line.strip())
        results_data = json.loads(results_line.strip())
        fhir_bundle = parse_fhir_bundle(eval_data["fhir"])
        patient = extract_patient_from_bundle(fhir_bundle)
        if not patient:
            continue
        for field, ops in field_map.items():
            total_field_comparisons += 1
            if (
                field.startswith("practitioner")
                or field.startswith("allergy")
                or field.startswith("immunization")
            ):
                # For practitioner, allergy, and immunization fields, use bundle data
                fhir_val = ops["extract_fhir"](fhir_bundle)
            else:
                # For patient fields, use patient data
                fhir_val = ops["extract_fhir"](patient)
            result_val = ops["extract_result"](results_data)
            if ops["compare"](result_val, fhir_val):
                stats[field] += 1
            else:
                failed_records[field].append(line_num)
                total_failed_comparisons += 1
        total += 1
    return stats, total, failed_records, total_field_comparisons, total_failed_comparisons


# --- Field Map Definitions ---
FIELD_MAP = {
    # Name fields
    "family": {
        "extract_fhir": lambda p: normalize_fhir_name(p.get("name", []))["family"],
        "extract_result": lambda r: r.get("name", {}).get("family") if r.get("name") else None,
        "compare": compare_strict,
    },
    "given": {
        "extract_fhir": lambda p: normalize_fhir_name(p.get("name", []))["given"],
        "extract_result": lambda r: r.get("name", {}).get("given") if r.get("name") else None,
        "compare": compare_strict,
    },
    "prefix": {
        "extract_fhir": lambda p: normalize_fhir_name(p.get("name", []))["prefix"],
        "extract_result": lambda r: r.get("name", {}).get("prefix") if r.get("name") else None,
        "compare": compare_strict,
    },
    # Address fields
    "line": {
        "extract_fhir": lambda p: normalize_fhir_address(p.get("address", []))["line"],
        "extract_result": lambda r: r.get("address", {}).get("line") if r.get("address") else None,
        "compare": compare_strict,
    },
    "city": {
        "extract_fhir": lambda p: normalize_fhir_address(p.get("address", []))["city"],
        "extract_result": lambda r: r.get("address", {}).get("city") if r.get("address") else None,
        "compare": compare_strict,
    },
    "state": {
        "extract_fhir": lambda p: normalize_fhir_address(p.get("address", []))["state"],
        "extract_result": lambda r: r.get("address", {}).get("state") if r.get("address") else None,
        "compare": compare_strict,
    },
    "postalCode": {
        "extract_fhir": lambda p: normalize_fhir_address(p.get("address", []))["postalCode"],
        "extract_result": lambda r: r.get("address", {}).get("postalCode")
        if r.get("address")
        else None,
        "compare": compare_strict,
    },
    "country": {
        "extract_fhir": lambda p: normalize_fhir_address(p.get("address", []))["country"],
        "extract_result": lambda r: r.get("address", {}).get("country")
        if r.get("address")
        else None,
        "compare": compare_strict,
    },
    # Simple fields
    "gender": {
        "extract_fhir": lambda p: p.get("gender"),
        "extract_result": lambda r: r.get("gender"),
        "compare": compare_case_insensitive,
    },
    "birthDate": {
        "extract_fhir": lambda p: p.get("birthDate"),
        "extract_result": lambda r: r.get("birthDate"),
        "compare": compare_strict,
    },
    "maritalStatus": {
        "extract_fhir": lambda p: normalize_fhir_marital_status(p.get("maritalStatus")),
        "extract_result": lambda r: r.get("maritalStatus"),
        "compare": compare_strict,
    },
    # Practitioner fields
    "practitioner": {
        "extract_fhir": lambda bundle: extract_all_practitioners_from_bundle(bundle),
        "extract_result": lambda r: combine_practitioner_name(r.get("practitioner", {}))
        if r.get("practitioner")
        else None,
        "compare": lambda result, fhir_list: (
            result in fhir_list
            if fhir_list and result
            else (result is None or result == "")
            and (not fhir_list or all(not item for item in fhir_list))
        ),
    },
    # Allergy fields
    "allergyRecordedCount": {
        "extract_fhir": extract_allergy_count_from_bundle,
        "extract_result": lambda r: len(r.get("allergy", {}).get("substance", []))
        if r.get("allergy", {}).get("substance")
        else 0,
        "compare": compare_strict,
    },
    # Immunization fields
    "immunizationCount": {
        "extract_fhir": extract_immunization_count_from_bundle,
        "extract_result": lambda r: len(r.get("immunization", [])),
        "compare": compare_strict,
    },
    "immunizationStatus": {
        "extract_fhir": extract_immunization_status_from_bundle,
        "extract_result": lambda r: [imm.get("status") for imm in r.get("immunization", []) if imm.get("status")],
        "compare": lambda result, fhir_list: (
            result[0] in fhir_list
            if result and fhir_list
            else (not result or not result[0])
            and (not fhir_list or all(not item for item in fhir_list))
        ),
    },
    "immunizationDate": {
        "extract_fhir": extract_immunization_dates_from_bundle,
        "extract_result": lambda r: [
            imm.get("occurrenceDateTime") or imm.get("occurrenceString")
            for imm in r.get("immunization", [])
            if imm.get("occurrenceDateTime") or imm.get("occurrenceString")
        ],
        "compare": lambda result, fhir_list: (
            result[0] in fhir_list
            if result and fhir_list
            else (not result or not result[0])
            and (not fhir_list or all(not item for item in fhir_list))
        ),
    },
}


# --- Reporting ---
def print_field_stats(
    stats, total, failed_records, total_field_comparisons, total_failed_comparisons
):
    print("=== INFORMATION EXTRACTION EVALUATION RESULTS ===\n")
    print(f"Total Records: {total}")
    for field, count in stats.items():
        print(f"{field}: {count}/{total} ({count/total*100:.1f}%)")
        if failed_records[field]:
            # Print only the first 10 failed IDs for brevity
            print(f" First 10 failed IDs: {failed_records[field][:10]}")

    total_passed_comparisons = total_field_comparisons - total_failed_comparisons
    print(
        dedent(
            f"""
        Overall accuracy (across all fields):
        {total_passed_comparisons}/{total_field_comparisons} ({total_passed_comparisons/total_field_comparisons*100:.1f}%)
        """
        )
    )
    print(f"Total comparisons: {total_field_comparisons}")
    print(f"Failed comparisons: {total_failed_comparisons}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate FHIR extraction results.")
    parser.add_argument(
        "--eval_file",
        "-e",
        type=str,
        default="../data/fhir.jsonl",
        help="Path to the evaluation (gold standard) file.",
    )
    parser.add_argument(
        "--results_file",
        "-r",
        type=str,
        default="../data/results/extracted_fhir.jsonl",
        help="Path to the results file.",
    )
    args = parser.parse_args()

    stats, total, failed_records, total_field_comparisons, total_failed_comparisons = (
        evaluate_fields(args.eval_file, args.results_file, FIELD_MAP)
    )
    print_field_stats(
        stats, total, failed_records, total_field_comparisons, total_failed_comparisons
    )
