"""Check the public aggregate exports against each other; no dependencies."""
import csv
import itertools
import json
import math
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
public = root / "docs" / "results"
catalog = json.loads((public / "catalog.json").read_text())
studies = {s["study"]: s for s in catalog["studies"]}
assert len(studies) == 29 and sum(s["n"] for s in studies.values()) == 55207
grid = itertools.product(
    [p["id"] for p in catalog["predictors"]],
    [o["id"] for o in catalog["outcomes"]],
    catalog["adjustments"], catalog["weighting"], catalog["estimators"],
)
expected, successful, unavailable = set(), 0, 0
for predictor, outcome, adjustment, weighting, estimator in grid:
    key = "__".join((predictor, outcome, adjustment, weighting, estimator))
    expected.add(key)
    model = json.loads((public / f"{key}.json").read_text())
    assert model["key"] == key
    assert len(model["rows"]) == 29
    assert {r["study"] for r in model["rows"]} == set(studies)
    for row in model["rows"]:
        assert 0 <= row["n"] <= studies[row["study"]]["n"]
        if row["status"] != "ok":
            unavailable += 1
            assert row["reason"]
            continue
        successful += 1
        assert row["n"] >= 80 and 0 < row["effective_n"] <= row["n"] + 1e-4
        for field in ("estimate", "lower", "upper", "se"):
            assert math.isfinite(row[field])
        assert row["lower"] <= row["estimate"] <= row["upper"]
        assert len(row["curve"]) == len(row["observed"]) == 4
        assert sum(p["n"] for p in row["observed"]) == row["n"]
        assert abs(row["estimate"] - (row["curve"][-1]["estimate"] - row["curve"][0]["estimate"])) < 3e-7
        if estimator == "logistic":
            assert all(0 <= p["estimate"] <= 1 for p in row["curve"])
    assert len(model["context"]) == 6
    for context in model["context"]:
        if context["status"] != "ok":
            continue
        included = context["studies"]
        assert len(included) == context["n"]
        assert len({studies[s]["country_cluster"] for s in included}) == context["clusters"]
        for s in included:
            assert studies[s][f"coverage_{context['timing']}"] >= context["threshold"] - 1e-7
        assert context["lower"] <= context["estimate"] <= context["upper"]

assert {p.stem for p in public.glob("*__*.json")} == expected
with (root / "tables" / "model_results.csv").open() as f:
    table = list(csv.DictReader(f))
assert len(table) == successful + unavailable == 9744
assert successful == 9408 and unavailable == 336
for outcome in catalog["outcomes"]:
    rows = json.loads((public / f"sensitivity_{outcome['id']}.json").read_text())
    assert len(rows) == 48 * 29
    assert {r["outcome"] for r in rows} == {outcome["id"]}

# Public result files contain no respondent identifiers or row-level inputs.
for file in public.glob("*.json"):
    text = file.read_text()
    assert "F1003_1" not in text and '"respondent_id"' not in text
assert not list((root / "docs").rglob("*.dta"))
standalone = root / "output" / "trust-democracy.html"
if standalone.exists():
    html = standalone.read_text()
    payload = re.search(r'<script id="embedded-results" type="application/json">(.*?)</script>', html, re.S)
    assert payload
    embedded = json.loads(payload.group(1))
    assert set(embedded) == {p.stem for p in public.glob("*.json")}
    for file in public.glob("*.json"):
        assert embedded[file.stem] == json.loads(file.read_text())
    assert 'src="assets/' not in html and 'href="assets/' not in html
    assert '<script src=' not in html
    print("Verified standalone HTML embeds every aggregate result and all runtime assets.")
print(f"Verified {len(expected)} specifications, {successful} available fits, {unavailable} explicit exclusions, all prediction contrasts and cabinet coverage.")
