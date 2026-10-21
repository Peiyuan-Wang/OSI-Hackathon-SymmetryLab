"""Bounded, journaled research loop. Scientific labels belong to the verifier."""

import json
from pathlib import Path
from time import monotonic
from symmetrylab.schemas import digest, read_json, write_json, SolverBudget
from symmetrylab.verifier.counterexample import PREDICATES, find_counterexample
from symmetrylab.verifier.gauge_solver import solve_gauge_equivalence
from symmetrylab.memory.lessons import make_lesson
from symmetrylab.observability.trace import Trace
from symmetrylab.communication.render import CORRECTION, AUDIENCES, freeze_result, render_report, audit_result

DEFAULTS = {"max_cases": 30, "max_seconds": 180, "max_model_calls": 6,
            "max_total_tokens": 12000, "max_output_tokens": 600}


def run_research(cases, output, mode="scripted", config=None, client=None, source=None,
                 predicate="nonzero_q_implies_nontrivial"):
    config = dict(DEFAULTS, **(config or {}))
    for key in DEFAULTS:
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if mode not in {"scripted", "live", "replay"}:
        raise ValueError("unknown mode")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("output directory must be empty; existing research is never overwritten")
    if mode == "replay":
        if not source:
            raise ValueError("replay requires --source from an existing completed run")
        frozen = read_json(Path(source) / "result.json")
        audit_result(frozen)
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / "replay.json", {"source_result_id": frozen["result_id"], "mode": "replay"})
        write_json(output / "result.json", frozen)
        for audience in AUDIENCES:
            (output / f"report_{audience}_en.md").write_text(render_report(frozen, audience), encoding="utf-8")
        return frozen
    # Fail closed before creating a run or sending any private input.
    cases = list(cases)
    if any(c.get("privacy") != "public_toy" for c in cases):
        raise ValueError("research demo accepts public_toy only")
    if mode == "live" and client is None:
        raise ValueError("live mode requires a configured model client")
    if predicate not in PREDICATES:
        raise ValueError("unsupported predicate")
    output.mkdir(parents=True, exist_ok=True)
    trace = Trace(output / "trace.jsonl")
    # Config logging is an allowlist; no key, headers or URL credentials are recorded.
    safe = {k: config[k] for k in DEFAULTS}
    safe.update(mode=mode, model=config.get("model") if mode == "live" else None,
                input_hashes=[digest(c) for c in cases])
    write_json(output / "config.json", safe)
    start = monotonic()
    calls, reserved_tokens, actual_tokens = 0, 0, 0
    usage_known = True

    def ask(messages):
        nonlocal calls, reserved_tokens, actual_tokens, usage_known
        # UTF-8 bytes are a conservative token estimate for byte-level API tokenizers;
        # provider framing is padded. This is a local budget, not a billing guarantee.
        reservation = len(json.dumps(messages, ensure_ascii=False).encode()) + 1024 + config["max_output_tokens"]
        if calls >= config["max_model_calls"] or reserved_tokens + reservation > config["max_total_tokens"]:
            raise RuntimeError("model call/token budget exceeded")
        remaining = config["max_seconds"] - (monotonic() - start)
        if remaining <= 0:
            raise RuntimeError("wall-clock budget exceeded")
        if hasattr(client, "timeout"):
            client.timeout = min(30, remaining)
        calls += 1
        reserved_tokens += reservation
        answer = client.complete(messages, config["max_output_tokens"])
        usage = answer.get("usage", {}).get("total_tokens")
        if usage is None:
            usage_known = False
            usage = 0
        if type(usage) is not int or usage < 0:
            raise RuntimeError("invalid model token usage")
        actual_tokens += usage
        if actual_tokens > config["max_total_tokens"]:
            raise RuntimeError("reported token budget exceeded")
        return json.loads(answer["content"])

    try:
        trace.emit("INIT", mode=mode)
        trace.emit("VALIDATE_TASK", cases=len(cases))
        if mode == "live":
            reply = ask([{"role": "system", "content": "Choose one executable research hypothesis. Reply JSON only: {\"predicate\": \"nonzero_q_implies_nontrivial\"} or {\"predicate\": \"individual_implies_joint\"}. These are conjectures, not facts."}])
            predicate = reply.get("predicate")
            if predicate not in PREDICATES:
                raise ValueError("model hypothesis is outside the executable whitelist")
        trace.emit("PROPOSE", predicate=predicate, statement=PREDICATES[predicate], controlled=mode == "scripted")
        trace.emit("GENERATE_CASES", scope="supplied public toy cases", count=len(cases))
        remaining = config["max_seconds"] - (monotonic() - start)
        search = find_counterexample(predicate, cases, config["max_cases"], remaining)
        evidence = search["evidence"]
        for entry in evidence:
            trace.emit("VERIFY", case_id=entry["case"]["case_id"], result=entry["result"])
        lessons = []
        revision_status = "not_attempted"
        if search["counterexample"]:
            entry = next(e for e in evidence if e["case"]["case_id"] == search["counterexample"])
            trace.emit("CRITIQUE", counterexample=search["counterexample"], reason="certificate contradicts executable hypothesis")
            lessons.append(make_lesson(predicate, entry))
            trace.emit("UPDATE_MEMORY", lesson=lessons[0])
            if mode == "live":
                reply = ask([{"role": "system", "content": "A verified counterexample refuted the hypothesis. Select the corrected criterion by returning JSON {\"criterion\":\"common_gauge_image\"}. Do not claim a new theorem."},
                             {"role": "user", "content": json.dumps({"hypothesis": predicate, "counterexample": entry, "lesson": lessons[0]}, ensure_ascii=False)}])
                if reply.get("criterion") != "common_gauge_image":
                    raise ValueError("model revision is unsupported")
            revision_status = "canonical_criterion_selected"
            trace.emit("REVISE", criterion=CORRECTION,
                       provenance="deterministic template" if mode == "scripted" else "model selected constrained criterion")
            # Recheck other examples after feedback; these are demonstrations of the
            # criterion, not proof that the model learned or that a theorem is new.
            seen = {e["case"]["case_id"] for e in evidence}
            for case in cases:
                if case["case_id"] in seen:
                    continue
                remaining = config["max_seconds"] - (monotonic() - start)
                if len(evidence) >= config["max_cases"] or remaining <= 0:
                    break
                answer = solve_gauge_equivalence(case, budget=SolverBudget(seconds=min(10, remaining)))
                evidence.append({"case": case, "result": answer})
                trace.emit("RECHECK", case_id=case["case_id"], result=answer)
        frozen = freeze_result({"mode": mode, "initial_predicate": predicate,
            "initial_statement": PREDICATES[predicate], "hypothesis_status": search["status"],
            "counterexample": search["counterexample"], "revision_status": revision_status,
            "search_scope": f"supplied finite domain ({len(cases)} cases), cap {config['max_cases']}",
            "evidence": evidence, "lessons": lessons,
            "metrics": {"model_calls": calls, "reserved_token_upper_estimate": reserved_tokens,
                        "provider_reported_tokens": actual_tokens if usage_known else None,
                        "elapsed_seconds": monotonic() - start,
                        "weight_updates": 0, "price": None}, "physical_scope": "toy_only"})
        trace.emit("FREEZE_RESULT", result_id=frozen["result_id"])
        write_json(output / "result.json", frozen)
        write_json(output / "memory.json", lessons)
        write_json(output / "metrics.json", frozen["metrics"])
        for audience in AUDIENCES:
            (output / f"report_{audience}_en.md").write_text(render_report(frozen, audience), encoding="utf-8")
        trace.emit("DONE", result_id=frozen["result_id"])
        return frozen
    except Exception:
        trace.emit("FAILED", message="run stopped; inspect local error, no scientific conclusion emitted")
        raise
