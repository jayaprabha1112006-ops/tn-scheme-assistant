from pathlib import Path

import pytest
import yaml

from engine import evaluate

CASES = yaml.safe_load(Path("eval/cases.yaml").read_text(encoding="utf-8"))


def ids(results, status):
    return {s["id"] for s, _fails, _missing, _notes in results[status]}


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_case(case):
    results = evaluate(case["profile"])
    assert ids(results, "eligible") == set(case["eligible"])
    assert ids(results, "maybe") == set(case["maybe"])