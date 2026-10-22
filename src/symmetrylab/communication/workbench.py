"""Deterministic audience views over exactly the same independently checked evidence."""
import json
from symmetrylab.verifier.certificate import verify_certificate

INTRO = {
    "researcher": "On T^d, solve (R_g − s_g I) theta = q_g mod Z^d simultaneously for all generators. Relations precede classification. Each instance below includes a checkable exact certificate.",
    "student": "A nonzero shift may disappear when we change the momentum origin. The test is whether one shared origin change removes every generator's shift. Exact arithmetic checks the answer.",
    "general": "Changing the origin can sometimes make a shift disappear. We check whether the same change works for every operation. A mathematical witness supports each verified example."
}


def render_agent_report(state, audience="researcher"):
    if audience not in INTRO:
        raise ValueError("unknown audience")
    if state.get("research_profile", {}).get("track", "legacy") != "legacy":
        from .discovery import render_discovery
        return render_discovery(state, audience)
    lines = ["# SymmetryLab Research Report", "", f"Mode: {state['mode']} | Run: {state['run_id']} | Status: {state['status']}", "",
             "## Research question", "", state["goal"], "", "## Reading guide", "", INTRO[audience], "",
             "Scope: abstract public toy actions only. Finite tests do not prove general theorems or physical realization.", ""]
    if state["mode"] == "demo":
        lines += ["This run uses a simulated offline policy. No live language model was called.", ""]
    lines += ["## Certified instance evidence", ""]
    cases = {c["case_id"]: c for c in state["candidates"]}
    for e in state["evidence"]:
        case, result = cases[e["candidate_id"]], e["result"]
        checked = e["certificate_verified"] and verify_certificate(case, result)
        relation = f" compared with {e['target_id']}" if e.get("target_id") else ""
        lines += [f"### {case['case_id']}: {case['label']}{relation}", "",
                  f"Solver status: {result['status']}. Independent certificate: {'verified' if checked else 'not verified'}.", "",
                  "```json", json.dumps({"operations": case["operations"], "result": result}, indent=2), "```", ""]
    lines += ["## Executable claim checks", "", "```json", json.dumps(state["claim_checks"], indent=2), "```", "",
              "## Hypotheses — unverified model proposals", ""]
    for hypothesis in state["hypotheses"]:
        lines += [f"- {hypothesis['id']}: {hypothesis['statement']}"]
    lines += ["", "## Synthesis — unverified model text", "", state.get("summary") or "No final synthesis was produced.", "",
              "## Limitations", ""] + ["- " + item for item in state["limitations"]]
    lines += ["", "## Metrics", "", "```json", json.dumps(state["metrics"], indent=2), "```", "",
              f"Evidence hash: {state.get('evidence_hash', 'run in progress')}", ""]
    return "\n".join(lines)
