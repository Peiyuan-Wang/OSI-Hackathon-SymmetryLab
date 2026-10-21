"""Label-separated benchmark runner. This is baseline E, not an LLM ablation."""

from pathlib import Path
from time import monotonic
from symmetrylab.schemas import read_json, write_json, digest
from symmetrylab.verifier.gauge_solver import solve_gauge_equivalence
from symmetrylab.verifier.certificate import verify_certificate


def load_suite(path, split=None):
    path = Path(path).resolve()
    manifest = read_json(path)
    loaded = []
    for spec in manifest["cases"]:
        if split is not None and spec["split"] != split:
            continue
        target = (path.parent / spec["path"]).resolve()
        if not target.is_relative_to(path.parent):
            raise ValueError("benchmark path escapes suite directory")
        case = read_json(target)
        loaded.append((case, spec))
    return loaded


def evaluate(suite, output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("evaluation output directory must be empty")
    start = monotonic()
    rows = []
    for case, spec in load_suite(suite):
        result = solve_gauge_equivalence(case)
        mathematical = result["status"] in {"gauge_trivial", "gauge_nontrivial"}
        cert_ok = verify_certificate(case, result) if mathematical else None
        rows.append({"case_id": case["case_id"], "split": spec["split"],
                     "expected": spec["expected"], "actual": result["status"],
                     "correct": result["status"] == spec["expected"] and cert_ok is not False,
                     "certificate_verified": cert_ok, "result": result})
    classified = [row for row in rows if row["certificate_verified"] is not None]
    correct = sum(row["correct"] for row in rows)
    metrics = {"arm": "E: deterministic verifier", "total": len(rows), "correct": correct,
               "accuracy": correct / len(rows) if rows else None,
               "mathematical_cases": len(classified),
               "certificates_verified": sum(row["certificate_verified"] for row in classified),
               "elapsed_seconds": monotonic() - start, "model_calls": 0,
               "manifest_hash": digest(read_json(suite)),
               "llm_ablation_status": "not_run", "heldout_status": "not_implemented"}
    write_json(output / "metrics.json", metrics)
    write_json(output / "results.json", rows)
    return metrics
