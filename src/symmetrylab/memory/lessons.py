"""Only certificate-backed counterexamples can become active lessons."""

from symmetrylab.verifier.counterexample import is_counterexample


def make_lesson(predicate, entry):
    if not is_counterexample(predicate, entry["case"], entry["result"]):
        raise ValueError("lesson requires a verified counterexample")
    return {
        "lesson_id": "L001", "predicate": predicate,
        "counterexample_id": entry["case"]["case_id"],
        "failure_type": "nonzero_is_not_obstruction" if predicate.startswith("nonzero") else "individual_is_not_joint",
        "strategy": "Validate group relations, then solve B*theta=q mod 1 for one common theta.",
        "scope": "fixed torus affine convention; public toys",
        "evidence_status": "certificate_verified",
        "input_hash": entry["result"]["input_hash"],
        "certificate": entry["result"]["certificate"],
    }
