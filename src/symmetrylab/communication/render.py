"""Audience templates consume one frozen, hashed scientific result."""

from symmetrylab.schemas import digest
from symmetrylab.verifier.certificate import verify_certificate

AUDIENCES = {"researcher": "Researchers", "student": "Physics students", "general": "Interdisciplinary readers"}
CORRECTION = "First validate the group relations, then check whether one common theta satisfies (R_g-s_g I)theta=q_g mod 1 for every generator."


def evidence_payload(result):
    return {k: v for k, v in result.items() if k not in {"evidence_hash", "result_id"}}


def audit_result(result):
    if result.get("evidence_hash") != digest(evidence_payload(result)):
        raise ValueError("frozen result hash mismatch")
    if result.get("result_id") != result["evidence_hash"][:16]:
        raise ValueError("result identity mismatch")
    from symmetrylab.verifier.group_relations import check_group_relations
    from symmetrylab.verifier.counterexample import is_counterexample
    for entry in result["evidence"]:
        if entry["result"]["status"] in {"gauge_trivial", "gauge_nontrivial"}:
            if not verify_certificate(entry["case"], entry["result"]):
                raise ValueError("certificate audit failed")
        elif entry["result"]["status"] != "budget_exceeded":
            if check_group_relations(entry["case"])["status"] != entry["result"]["status"]:
                raise ValueError("input status audit failed")
    if result.get("counterexample"):
        entries = [e for e in result["evidence"] if e["case"]["case_id"] == result["counterexample"]]
        if len(entries) != 1 or not is_counterexample(result["initial_predicate"], entries[0]["case"], entries[0]["result"]):
            raise ValueError("hypothesis counterexample audit failed")


def freeze_result(result):
    result["evidence_hash"] = digest(evidence_payload(result))
    result["result_id"] = result["evidence_hash"][:16]
    audit_result(result)
    return result


def render_report(result, audience="researcher", language="en"):
    if audience not in AUDIENCES or language != "en":
        raise ValueError("supported audiences: researcher/student/general; language: en")
    audit_result(result)
    from symmetrylab.verifier.counterexample import PREDICATES
    # Render the canonical predicate in English even when replaying a legacy run.
    # The frozen payload, evidence hash and mathematical result remain intact.
    statement = PREDICATES[result["initial_predicate"]]
    lines = ["# SymmetryLab Research Report", "", f"Audience: {AUDIENCES[audience]}",
             f"Mode: {result['mode']} (scripted uses a preset hypothesis; replay renders an existing result)",
             f"Result ID: {result['result_id']}", f"Evidence hash: {result['evidence_hash']}",
             "Physical scope: toy_only (abstract toy actions)", "",
             f"Conclusion status: {result['hypothesis_status']}",
             f"Initial hypothesis: {statement}",
             f"Verified counterexample: {result.get('counterexample') or 'None found within the supplied finite domain'}", ""]
    if result.get("counterexample"):
        lines += ["Revised criterion: " + CORRECTION]
    if audience == "researcher":
        lines += ["", "On T^d=R^d/Z^d, fix F_g(k)=s_g R_g k+s_g q_g and the coordinate change k'=k+theta.",
                  "R_g is an invertible integer matrix, s_g is a sign character taking values ±1, and q_g is a rational shift. Congruences are modulo the integer lattice.",
                  "Stack B=stack(R_g-s_g I) and q=stack(q_g). The computation tests whether the given cocycle lies in the image of the common gauge map."]
    elif audience == "student":
        lines += ["", "q describes a shift in momentum coordinates, and theta describes a single change of momentum origin. A nonzero shift can sometimes be removed by changing the origin.",
                  "The same theta must work for every symmetry operation. Separate solutions for individual generators do not establish a common solution."]
    else:
        lines += ["", "Think of the symmetry operations as different transformations of coordinates. We test whether one change of origin can remove all their shifts at once.",
                  "The program provides an exactly checkable fractional solution or evidence of impossibility. Every explanation uses the same computation record."]
    lines += ["", "## Computational evidence", "", "| Case | Classification | Fractional solution / evidence |", "|---|---|---|"]
    for entry in result["evidence"]:
        case, answer = entry["case"], entry["result"]
        cert = answer.get("certificate") or {}
        detail = str(answer["theta"]) if answer.get("theta") else cert.get("kind", answer.get("message") or "See relation residuals")
        lines.append(f"| {case['case_id']} | {answer['status']} | {detail} |")
    lines += ["", f"Search scope: {result['search_scope']}. Recorded cases: {len(result['evidence'])}.",
              "Passing finite tests does not prove a theorem for an infinite family. These are abstract torus affine toy models; physical SSG realizations, materials, and novelty have not been checked.",
              "No model weights were updated. Lessons guide revisions to the tool-use strategy.", ""]
    return "\n".join(lines)
