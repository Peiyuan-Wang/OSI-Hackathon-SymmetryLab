"""Data-only research tools. Candidate generation is controlled by model arguments."""
from copy import deepcopy
from itertools import product, islice
from fractions import Fraction
from time import monotonic
from symmetrylab.schemas import CONVENTION, SolverBudget
from symmetrylab.verifier.group_relations import presentation, validate_case, check_group_relations
from symmetrylab.verifier.gauge_solver import solve_gauge_equivalence
from symmetrylab.verifier.certificate import verify_certificate
from symmetrylab.verifier.counterexample import PREDICATES, is_counterexample


class ResearchTools:
    def __init__(self, state, deadline, cancelled, max_candidates=40):
        self.state, self.deadline, self.cancelled = state, deadline, cancelled
        self.max_candidates = max_candidates

    def remaining(self):
        if self.cancelled():
            raise InterruptedError("Run cancelled")
        seconds = self.deadline - monotonic()
        if seconds <= 0:
            raise TimeoutError("Wall-time budget exhausted")
        return min(5, seconds)

    def candidate(self, identifier):
        for case in self.state["candidates"]:
            if case["case_id"] == identifier:
                return case
        raise ValueError("unknown candidate_id")

    def register_candidate(self, label, dimension, group, operations):
        self.remaining()
        if len(self.state["candidates"]) >= self.max_candidates:
            raise ValueError("candidate budget exhausted")
        if not isinstance(label, str) or not 1 <= len(label) <= 120:
            raise ValueError("label must contain 1–120 characters")
        if not isinstance(operations, list) or not 1 <= len(operations) <= 2:
            raise ValueError("one or two operations required")
        names = ["g"] if len(operations) == 1 else ["a", "b"]
        case = {"schema_version": "1.0", "case_id": f"C{len(self.state['candidates']) + 1:03d}",
                "label": label, "dimension": dimension, "convention": CONVENTION,
                "privacy": "public_toy", "physical_scope": "toy_only",
                "group": {"name": group, "generators": names, "relators": presentation(group, names)},
                "operations": [dict(op, name=n) for op, n in zip(operations, names)]}
        validation = validate_case(case)
        if validation["status"] != "valid":
            return validation
        self.state["candidates"].append(case)
        return {"status": "registered", "candidate_id": case["case_id"], "case": case,
                "relations": check_group_relations(case)}

    def check_relations(self, candidate_id):
        return check_group_relations(self.candidate(candidate_id))

    def solve_gauge(self, candidate_id, target_id=None):
        case = self.candidate(candidate_id)
        target_q = None
        if target_id:
            target = self.candidate(target_id)
            if (case["group"] != target["group"] or case["dimension"] != target["dimension"]
                    or [(o["R"], o["s"]) for o in case["operations"]] != [(o["R"], o["s"]) for o in target["operations"]]):
                raise ValueError("comparison requires the same ordered linear action")
            target_q = [o["q"] for o in target["operations"]]
        result = solve_gauge_equivalence(case, target_q, SolverBudget(seconds=self.remaining()))
        checked = result["status"] in {"gauge_trivial", "gauge_nontrivial"} and verify_certificate(case, result)
        entry = {"candidate_id": candidate_id, "target_id": target_id, "result": result,
                 "certificate_verified": bool(checked)}
        self.state["evidence"].append(entry)
        return entry

    def compare_gauge(self, candidate_id, target_id):
        return self.solve_gauge(candidate_id, target_id)

    def test_claim(self, predicate, candidate_ids):
        if predicate not in PREDICATES or not isinstance(candidate_ids, list) or not 1 <= len(candidate_ids) <= 20:
            raise ValueError("use a supported predicate and 1–20 candidate IDs")
        counterexamples, unresolved, excluded = [], [], []
        for cid in dict.fromkeys(candidate_ids):
            entry = self.solve_gauge(cid)
            if entry["result"]["status"] in {"invalid_input", "relation_inconsistent"}:
                excluded.append(cid)
            elif not entry["certificate_verified"]:
                unresolved.append(cid)
            elif is_counterexample(predicate, self.candidate(cid), entry["result"], self.remaining()):
                counterexamples.append(cid)
        result = {"predicate": predicate, "statement": PREDICATES[predicate], "domain": candidate_ids,
                  "counterexamples": counterexamples, "unresolved": unresolved, "excluded_invalid": excluded,
                  "status": "Counterexample found" if counterexamples else "No counterexample found in this finite domain"}
        if unresolved and not counterexamples:
            result["status"] = "incomplete"
        self.state["claim_checks"].append(result)
        if counterexamples:
            self.state["lessons"].append({"predicate": predicate, "counterexamples": counterexamples,
                                         "lesson": "This universal claim is refuted. Retain its exact counterexamples when revising the hypothesis."})
        return result

    def scan_shifts(self, candidate_id, denominator=2, max_cases=8):
        if type(denominator) is not int or not 1 <= denominator <= 4 or type(max_cases) is not int or not 1 <= max_cases <= 16:
            raise ValueError("denominator must be 1–4; max_cases must be 1–16")
        base = self.candidate(candidate_id)
        d, n = base["dimension"], len(base["operations"])
        scanned = []
        for values in islice(product(range(denominator), repeat=d * n), max_cases):
            self.remaining()
            ops = deepcopy(base["operations"])
            for i, op in enumerate(ops):
                op["q"] = [str(Fraction(x, denominator)) for x in values[i*d:(i+1)*d]]
            registered = self.register_candidate("Shift scan", d, base["group"]["name"], ops)
            scanned.append(self.solve_gauge(registered["candidate_id"]))
        return {"status": "finite_scan", "denominator": denominator, "domain_size": denominator ** (d*n),
                "truncated": len(scanned) < denominator ** (d*n), "results": scanned}

    def call(self, name, arguments):
        self.remaining()
        if name not in {"register_candidate", "check_relations", "solve_gauge", "compare_gauge", "scan_shifts", "test_claim"}:
            raise ValueError("tool is not registered")
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be an object")
        return getattr(self, name)(**arguments)
