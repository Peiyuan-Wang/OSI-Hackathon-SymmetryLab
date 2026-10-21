"""Iterative, budgeted model controller with independently certified facts."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from time import monotonic
from symmetrylab.schemas import digest, write_json
from symmetrylab.tools.research import ResearchTools
from .prompt import SYSTEM_PROMPT

DEFAULT_LIMITS = {"max_model_calls": 24, "max_tool_calls": 24, "max_candidates": 40,
                  "max_total_tokens": 180000, "max_output_tokens": 1600, "max_seconds": 240}
HARD_LIMITS = {"max_model_calls": 50, "max_tool_calls": 50, "max_candidates": 80,
               "max_total_tokens": 500000, "max_output_tokens": 8000, "max_seconds": 900}


def limits_from(config):
    limits = dict(DEFAULT_LIMITS, **config.get("limits", {}))
    for key, value in limits.items():
        if key not in HARD_LIMITS or type(value) is not int or not 1 <= value <= HARD_LIMITS[key]:
            raise ValueError(f"invalid budget: {key}")
    return limits


def text_field(action, name, max_length=2400):
    value = action.get(name)
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"{name} must be a nonempty bounded string")
    return value


def text_list(action, name):
    value = action.get(name)
    if not isinstance(value, list) or len(value) > 12 or any(not isinstance(x, str) or len(x) > 600 for x in value):
        raise ValueError(f"{name} must be a list of up to 12 short strings")
    return value


def run_agent(goal, output, mode="demo", config=None, client=None, cancelled=lambda: False, on_update=lambda state: None):
    config = config or {}
    limits = limits_from(config)
    if mode not in {"demo", "live"} or not isinstance(goal, str) or not 1 <= len(goal.strip()) <= 4000:
        raise ValueError("select demo/live and provide a goal of 1–4000 characters")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("run output must be a new or empty directory")
    if client is None:
        if mode == "demo":
            from symmetrylab.model.simulated import SimulatedPolicy
            client = SimulatedPolicy()
        else:
            from symmetrylab.model.client import OpenAICompatibleClient
            client = OpenAICompatibleClient(config)
    output.mkdir(parents=True, exist_ok=True)
    start = monotonic()
    state = {"schema_version": "2.0", "kind": "agent_research", "run_id": output.name, "mode": mode,
             "goal": goal.strip(), "status": "running", "created_at": datetime.now(timezone.utc).isoformat(),
             "plan": [], "hypotheses": [], "candidates": [], "evidence": [], "claim_checks": [], "lessons": [],
             "events": [], "summary": None, "limitations": [], "last_observation": None,
             "limits": limits, "metrics": {"policy_turns": 0, "model_calls": 0, "tool_calls": 0,
             "estimated_tokens_reserved": 0, "reported_tokens": 0, "usage_missing_calls": 0, "elapsed_seconds": 0}}
    tools = ResearchTools(state, start + limits["max_seconds"], cancelled, limits["max_candidates"])

    def event(kind, data):
        item = {"index": len(state["events"]) + 1, "kind": kind, "data": data, "seconds": round(monotonic()-start, 2)}
        state["events"].append(item)
        state["metrics"]["elapsed_seconds"] = round(monotonic()-start, 2)
        with (output / "trace.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        temp = output / "state.tmp"
        write_json(temp, state)
        temp.replace(output / "state.json")
        on_update(deepcopy(state))

    invalid = 0
    try:
        event("started", {"mode": mode, "policy": "Simulated offline policy" if mode == "demo" else "Live model"})
        for _ in range(limits["max_model_calls"]):
            tools.remaining()
            if state["metrics"]["reported_tokens"] >= limits["max_total_tokens"]:
                raise TimeoutError("Reported token budget exhausted")
            snapshot = {k: v for k, v in state.items() if k not in {"events", "created_at"}}
            messages = [{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(snapshot, ensure_ascii=False)}]
            # A deliberately conservative UTF-8-byte estimate, not a tokenizer count.
            reserve = len(json.dumps(messages, ensure_ascii=False).encode()) + 1024 + limits["max_output_tokens"]
            if state["metrics"]["estimated_tokens_reserved"] + reserve > limits["max_total_tokens"]:
                raise TimeoutError("Estimated token budget exhausted")
            state["metrics"]["estimated_tokens_reserved"] += reserve
            state["metrics"]["policy_turns"] += 1
            if mode == "live":
                state["metrics"]["model_calls"] += 1
            if hasattr(client, "timeout"):
                client.timeout = min(30, max(0.1, tools.deadline - monotonic()))
            event("thinking", {"turn": state["metrics"]["policy_turns"]})
            reply = client.complete(messages, limits["max_output_tokens"])
            tools.remaining()
            usage = reply.get("usage") or {}
            total = usage.get("total_tokens")
            if type(total) is int and total >= 0:
                state["metrics"]["reported_tokens"] += total
            elif mode == "live":
                state["metrics"]["usage_missing_calls"] += 1
            try:
                content = reply["content"]
                if not isinstance(content, str) or len(content) > 24000:
                    raise ValueError("action exceeds size limit")
                action = json.loads(content)
                if not isinstance(action, dict):
                    raise ValueError("action must be an object")
                kind = action.get("action")
                if kind == "plan":
                    steps = text_list(action, "steps")
                    if not steps:
                        raise ValueError("plan requires at least one step")
                    state["plan"] = steps
                    observation = {"status": "plan_updated", "steps": steps}
                elif kind == "hypothesis":
                    hypothesis = {"id": f"H{len(state['hypotheses'])+1:03d}", "statement": text_field(action, "statement"),
                                  "assumptions": text_list(action, "assumptions"), "status": "Unverified proposal"}
                    state["hypotheses"].append(hypothesis)
                    observation = hypothesis
                elif kind == "tool":
                    if state["metrics"]["tool_calls"] >= limits["max_tool_calls"]:
                        raise TimeoutError("Tool-call budget exhausted")
                    name = text_field(action, "name", 40)
                    state["metrics"]["tool_calls"] += 1
                    event("tool_call", {"name": name, "arguments": action.get("arguments", {}), "reason": action.get("reason", "")})
                    observation = tools.call(name, action.get("arguments", {}))
                elif kind == "finish":
                    state["summary"] = text_field(action, "summary")
                    state["limitations"] = text_list(action, "limitations")
                    state["status"] = "completed" if any(e["certificate_verified"] for e in state["evidence"]) else "incomplete"
                    event("synthesis", {"text": state["summary"], "status": "Unverified model synthesis"})
                    break
                else:
                    raise ValueError("unknown action; use plan, hypothesis, tool or finish")
                invalid = 0
                state["last_observation"] = observation
                event(kind, {"action": action, "observation": observation})
            except (ValueError, TypeError, KeyError, NotImplementedError) as exc:
                invalid += 1
                state["last_observation"] = {"status": "action_error", "message": str(exc)[:400]}
                event("action_error", state["last_observation"])
                if invalid >= 3:
                    state["status"] = "failed"
                    state["limitations"].append("Three consecutive malformed actions; correct the model or goal and start a new run.")
                    break
        else:
            raise TimeoutError("Model-turn budget exhausted")
    except InterruptedError:
        state["status"] = "cancelled"
    except TimeoutError as exc:
        state["status"] = "budget_exceeded"
        state["limitations"].append(str(exc))
    except (RuntimeError, OSError) as exc:
        state["status"] = "failed"
        state["limitations"].append(str(exc))
    state["evidence_hash"] = digest({"candidates": state["candidates"], "evidence": state["evidence"], "claim_checks": state["claim_checks"]})
    event("finished", {"status": state["status"], "evidence_hash": state["evidence_hash"]})
    write_json(output / "result.json", state)
    from symmetrylab.communication.workbench import render_agent_report
    for audience in ("researcher", "student", "general"):
        (output / f"report_{audience}_en.md").write_text(render_agent_report(state, audience), encoding="utf-8")
    return state
