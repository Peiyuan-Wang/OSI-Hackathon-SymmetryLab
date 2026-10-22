"""Deterministic audience views over exactly the same independently checked evidence."""
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
    lines += ["## Certified instance evidence", "", "| Candidate | Action | Result | θ | Certificate |", "|---|---|---|---|---|"]
    cases = {c["case_id"]: c for c in state["candidates"]}
    for e in state["evidence"]:
        case, result = cases[e["candidate_id"]], e["result"]
        checked = e["certificate_verified"] and verify_certificate(case, result)
        relation = f" vs {e['target_id']}" if e.get("target_id") else ""
        action = "; ".join(f"R={op['R']}, s={op['s']}, q={op['q']}" for op in case["operations"])
        theta = ", ".join(result["theta"]) if result.get("theta") else "—"
        lines.append(f"| {case['case_id']} {case['label']}{relation} | `{action}` | {result['status'].replace('_', ' ')} | {theta} | {'verified' if checked else 'not verified'} |")
    if not state["evidence"]:
        lines.append("| — | — | no evidence | — | — |")
    lines += ["", "Full certificates are in the evidence JSON.", "", "## Executable claim checks", ""]
    for claim in state["claim_checks"]:
        lines.append(f"- \"{claim['statement']}\" — {claim['status']}" + (f" ({', '.join(claim['counterexamples'])})" if claim["counterexamples"] else ""))
    lines += ["", "## Hypotheses — unverified model proposals", ""]
    for hypothesis in state["hypotheses"]:
        lines += [f"- {hypothesis['id']}: {hypothesis['statement']}"]
    lines += ["", "## Synthesis — unverified model text", "", state.get("summary") or "No final synthesis was produced.", "",
              "## Limitations", ""] + ["- " + item for item in state["limitations"]]
    m = state["metrics"]
    lines += ["", "---", "", f"Model calls {m['model_calls']} · policy steps {m['policy_turns']} · tool calls {m['tool_calls']} · {m['elapsed_seconds']} s", "",
              f"Evidence hash: {state.get('evidence_hash', 'run in progress')}", ""]
    return "\n".join(lines)
