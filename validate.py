import re
import sys
from pathlib import Path

import yaml

SCHEMES_DIR = Path("data/schemes")

REQUIRED_TOP = [
    "id", "name_en", "department", "scheme_type", "level",
    "benefit", "eligibility", "documents", "application",
    "official_url", "source_checked_on",
]
SCHEME_TYPES = {"state", "central"}
LEVELS = {"school", "college"}
COMMUNITIES = {"BC", "MBC", "DNC", "SC", "ST", "AD", "AD_CHRISTIAN", "OC", "any"}
APPLY_MODES = {"online", "offline"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def as_list(value):
    return value if isinstance(value, list) else [value]


def check_file(path, seen_ids):
    errors, warnings = [], []

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"invalid YAML: {e}"], []

    if not isinstance(data, dict):
        return ["file is empty or not a YAML mapping"], []

    for key in REQUIRED_TOP:
        if key not in data or data[key] in (None, "", []):
            errors.append(f"missing or empty field: {key}")

    # id rules
    sid = data.get("id")
    if sid:
        if sid != path.stem:
            errors.append(f"id '{sid}' does not match filename '{path.stem}'")
        if sid in seen_ids:
            errors.append(f"duplicate id: {sid}")
        seen_ids.add(sid)

    # simple value checks
    if data.get("scheme_type") not in SCHEME_TYPES:
        errors.append(f"scheme_type must be one of {sorted(SCHEME_TYPES)}")

    levels = data.get("level") or []
    for lv in as_list(levels):
        if lv not in LEVELS:
            errors.append(f"unknown level: {lv}")

    elig = data.get("eligibility") or {}
    if not isinstance(elig, dict):
        errors.append("eligibility must be a mapping")
        elig = {}
    if "state" not in elig:
        errors.append("eligibility.state is missing")

    if "community" in elig:
        for c in as_list(elig["community"]):
            if c not in COMMUNITIES:
                errors.append(f"unknown community code: {c}")

    for cr in elig.get("conditional_rules", []) or []:
        for c in as_list(cr.get("applies_to_community", [])):
            if c not in COMMUNITIES:
                errors.append(f"unknown community code in conditional_rules: {c}")

    # income must be a number or null, never text
    income = elig.get("max_family_income_inr")
    if income is not None and not isinstance(income, (int, float)):
        errors.append("max_family_income_inr must be a number or null")

    app = data.get("application") or {}
    if isinstance(app, dict) and app.get("mode") not in APPLY_MODES:
        errors.append(f"application.mode must be one of {sorted(APPLY_MODES)}")

    if not isinstance(data.get("documents"), list):
        errors.append("documents must be a list")

    date = str(data.get("source_checked_on", ""))
    if not DATE_RE.match(date):
        errors.append("source_checked_on must look like 2026-11-02")

    # warnings (not fatal)
    url = str(data.get("official_url", ""))
    if not url.startswith("http"):
        warnings.append("official_url is not a real link yet")
    if data.get("verified_on_official_site") is False:
        warnings.append("not yet verified on the official department site")

    return errors, warnings


def main():
    files = sorted(SCHEMES_DIR.glob("*.yaml"))
    if not files:
        print(f"No .yaml files found in {SCHEMES_DIR}")
        sys.exit(1)

    seen_ids = set()
    total_errors = 0

    for path in files:
        errors, warnings = check_file(path, seen_ids)
        status = "FAIL" if errors else "ok"
        print(f"[{status}] {path.name}")
        for e in errors:
            print(f"    ERROR:   {e}")
        for w in warnings:
            print(f"    warning: {w}")
        total_errors += len(errors)

    print(f"\n{len(files)} files checked, {total_errors} errors")
    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()