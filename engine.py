from pathlib import Path

import yaml

SCHEMES_DIR = Path("data/schemes")
KNOWN_SCHOOL_TYPES = {"government", "government_aided", "private"}


def load_schemes():
    return [yaml.safe_load(p.read_text(encoding="utf-8"))
            for p in sorted(SCHEMES_DIR.glob("*.yaml"))]


def as_list(v):
    return v if isinstance(v, list) else [v]


def check_scheme(scheme, p):
    """Return (reasons it fails, profile fields still missing, notes)."""
    e = scheme["eligibility"]
    fails, missing, notes = [], [], []

    def rule(field, ok, fail_msg):
        v = p.get(field)
        if v is None:
            if field not in missing:
                missing.append(field)
        elif not ok(v):
            fails.append(fail_msg)

    # --- rules that apply to every scheme ---
    if e.get("state", "any") != "any":
        rule("state", lambda v: v == e["state"], f"only for residents of {e['state']}")

    levels = as_list(scheme["level"])
    rule("stage", lambda v: v in levels, "is for " + "/".join(levels) + " students")

    community = e.get("community", "any")
    if community != "any":
        rule("community", lambda v: v in as_list(community),
             "only for " + ", ".join(as_list(community)) + " communities")

    if e.get("max_family_income_inr") is not None:
        rule("family_income", lambda v: v <= e["max_family_income_inr"],
             f"family income must be at most {e['max_family_income_inr']}")

    if e.get("disability_percent_min") is not None:
        rule("disability_percent", lambda v: v >= e["disability_percent_min"],
             f"needs disability of {e['disability_percent_min']}% or more")

    if e.get("must_not_hold_other_scholarship"):
        rule("holds_other_scholarship", lambda v: v is False,
             "cannot hold another scholarship")

    # rules that apply only to some communities (e.g. BC only)
    for cr in e.get("conditional_rules", []) or []:
        if p.get("community") in as_list(cr["applies_to_community"]):
            if "max_family_income_inr" in cr:
                rule("family_income", lambda v: v <= cr["max_family_income_inr"],
                     f"for {p['community']} students, family income must be at most "
                     f"{cr['max_family_income_inr']}")
            if cr.get("no_graduate_in_family"):
                rule("graduate_in_family", lambda v: v is False,
                     f"for {p['community']} students, no graduate allowed in the family")

    # --- school-only rules ---
    if p.get("stage") == "school":
        if "classes" in e:
            rule("class", lambda v: v in e["classes"], f"only for classes {e['classes']}")
        if "max_class" in e:
            rule("class", lambda v: v <= e["max_class"], f"only up to class {e['max_class']}")
        if "qualification_levels" in e:  # simplified: post-matric means class 11+
            rule("class", lambda v: v >= 11, "only for class 11 and above")
        # skip schemes whose school_type labels we haven't normalised yet
        if "school_type" in e and set(e["school_type"]) <= KNOWN_SCHOOL_TYPES:
            rule("school_type", lambda v: v in e["school_type"], "school type not covered")
        if "medium_of_instruction" in e:
            rule("medium", lambda v: v == e["medium_of_instruction"],
                 f"only for {e['medium_of_instruction']} medium")
        if e.get("tamil_first_language"):
            rule("tamil_first_language", lambda v: v is True,
                 "must have studied Tamil as first language")

    # --- college-only rules ---
    if p.get("stage") == "college":
        if "course_types" in e:
            rule("degree_type", lambda v: v in e["course_types"],
                 f"only for {e['course_types']} courses")
        if "allowed_degrees" in e:
            rule("degree", lambda v: v in e["allowed_degrees"],
                 f"only for {e['allowed_degrees']}")
        if "institution_type" in e:
            rule("institution_type", lambda v: v in e["institution_type"],
                 "college type not covered")

        if e.get("award_basis") == "merit_rank":
            notes.append("Prize depends on your rank, so you can apply but are not guaranteed it.")

        if fails:  # no point asking questions about a scheme already ruled out
            missing = []

        return fails, missing, notes


def evaluate(profile):
    results = {"eligible": [], "maybe": [], "not eligible": []}
    for s in load_schemes():
        fails, missing, notes = check_scheme(s, profile)
        status = "not eligible" if fails else ("maybe" if missing else "eligible")
        results[status].append((s, fails, missing, notes))
    return results


def show(title, profile):
    print("=" * 60)
    print(title)
    results = evaluate(profile)
    for status in ("eligible", "maybe", "not eligible"):
        print(f"\n{status.upper()} ({len(results[status])})")
        for s, fails, missing, notes in results[status]:
            print(f"  - {s['name_en']}")
            for f in fails:
                print(f"      x {f}")
            if missing:
                print(f"      ? need to know: {', '.join(missing)}")
            for n in notes:
                print(f"      * {n}")


if __name__ == "__main__":
    show("A: MBC girl, class 11, English medium, govt school", {
        "state": "Tamil Nadu", "stage": "school", "class": 11,
        "community": "MBC", "school_type": "government", "medium": "english",
        "tamil_first_language": True, "family_income": 90000,
        "disability_percent": 0, "holds_other_scholarship": False,
        "graduate_in_family": False,
    })
    show("B: BC student, BSc at a govt-aided arts college", {
        "state": "Tamil Nadu", "stage": "college", "degree": "BSc",
        "degree_type": "UG", "institution_type": "government_aided_arts_science",
        "community": "BC", "family_income": 150000, "disability_percent": 0,
        "holds_other_scholarship": False,
    })
    show("C: BC student, class 10, 50% disability", {
        "state": "Tamil Nadu", "stage": "school", "class": 10,
        "community": "BC", "school_type": "government", "medium": "tamil",
        "tamil_first_language": True, "family_income": 180000,
        "disability_percent": 50, "holds_other_scholarship": False,
        "graduate_in_family": False,
    })