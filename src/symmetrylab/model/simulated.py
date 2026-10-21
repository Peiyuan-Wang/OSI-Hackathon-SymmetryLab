"""Explicit offline demonstration policy; no model or benchmark-answer access."""
import json


class SimulatedPolicy:
    def complete(self, messages, max_tokens):
        state = json.loads(messages[-1]["content"])
        if not state["plan"]:
            action = {"action": "plan", "steps": ["Propose a falsifiable shift criterion", "Construct and verify an inversion", "Retain the counterexample and revise", "Compare a translation action"], "reason": "A compact counterexample search exposes the gauge distinction."}
        elif not state["hypotheses"]:
            action = {"action": "hypothesis", "statement": "Every nonzero shift is gauge-nontrivial.", "assumptions": ["Valid C2 affine action on a torus"]}
        elif not state["candidates"]:
            action = self.tool("register_candidate", label="Inversion with a half shift", dimension=2, group="C2", operations=[{"R": [[-1, 0], [0, -1]], "s": 1, "q": ["1/2", 0]}])
        elif not state["claim_checks"]:
            action = self.tool("test_claim", predicate="nonzero_q_implies_nontrivial", candidate_ids=[state["candidates"][0]["case_id"]])
        elif len(state["hypotheses"]) == 1:
            action = {"action": "hypothesis", "statement": "Nonzero shifts can be gauge-trivial; test whether a common theta removes all shifts.", "assumptions": ["The registered action satisfies its group relations", "The exact certificate is independently checked"]}
        elif len(state["candidates"]) == 1:
            action = self.tool("register_candidate", label="Translation by half a period", dimension=2, group="C2", operations=[{"R": [[1, 0], [0, 1]], "s": 1, "q": ["1/2", 0]}])
        elif not any(e["candidate_id"] == state["candidates"][1]["case_id"] for e in state["evidence"]):
            action = self.tool("solve_gauge", candidate_id=state["candidates"][1]["case_id"])
        else:
            action = {"action": "finish", "summary": "The inversion example refutes the nonzero-shift criterion. The translation example has an exact obstruction. Joint gauge equations decide these toy instances.", "limitations": ["Simulated policy: no live model was called", "Two abstract examples do not classify all actions or establish physical realization"]}
        return {"content": json.dumps(action), "usage": {}}

    @staticmethod
    def tool(name, **arguments):
        return {"action": "tool", "name": name, "arguments": arguments, "reason": "Follow the current plan using exact mathematical feedback."}
