"""Iterative, budgeted model controller with independently certified facts."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from time import monotonic
from symmetrylab.schemas import digest, write_json
from symmetrylab.tools.research import ResearchTools
from .prompt import SYSTEM_PROMPT, DISCOVERY_SYSTEM
from .profile import research_profile
from symmetrylab.model.actions import first_action

DEFAULT_LIMITS = {"max_model_calls": 24, "max_tool_calls": 24, "max_candidates": 40,
                  "max_total_tokens": 180000, "max_output_tokens": 1600, "max_seconds": 240}
HARD_LIMITS = {"max_model_calls": 50, "max_tool_calls": 50, "max_candidates": 80,
               "max_total_tokens": 500000, "max_output_tokens": 8000, "max_seconds": 900}


def limits_from(config):
    defaults = dict(DEFAULT_LIMITS)
    profile = config.get("research_profile", {})
    if isinstance(profile, dict) and profile.get("track") in {"theory", "experiment"}:
        defaults.update(max_seconds=600, max_total_tokens=400000)
    limits = dict(defaults, **config.get("limits", {}))
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
    profile = research_profile(config.get("research_profile"))
    if mode not in {"demo", "live"} or not isinstance(goal, str) or not 1 <= len(goal.strip()) <= 4000:
        raise ValueError("select demo/live and provide a goal of 1–4000 characters")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("run output must be a new or empty directory")
    if client is None:
        if mode == "demo":
            from symmetrylab.model.simulated import SimulatedPolicy
            if profile["track"] == "legacy":
                client = SimulatedPolicy()
            else:
                from symmetrylab.model.discovery_demo import DiscoveryDemo
                client = DiscoveryDemo()
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
    style = config.get("style_prompt")
    if style is not None and (not isinstance(style, str) or not 1 <= len(style) <= 4000):
        raise ValueError("style_prompt must be 1–4000 characters")
    state["style_profile"] = ({"hash": config.get("style_hash", digest(style)[:16]), "applied": mode == "live"} if style else None)
    state.update(research_profile=profile, sources=[], retrievals=[], structure_assessments=[],
                 calculations=[], directions=[], experiment_designs=[], taste_profile=[], recalled_lessons=[])
    if profile["reuse_lessons"]:
        from symmetrylab.memory.discovery import recall_lessons
        state["recalled_lessons"] = recall_lessons(output.parent, profile["track"], mode, goal=goal, material=profile.get("material", ""))
    from symmetrylab.memory.discovery import recall_preferences
    state["preference_feedback"] = recall_preferences(output.parent, profile) if profile["track"] != "legacy" else []
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
            if profile["track"] != "legacy":
                snapshot["controller_instruction"] = (
                    "This is a continuing loop, not a fresh task. A plan already exists. Choose ONE tool action now using last_observation; do not restart planning or simulate tool outputs."
                    if state["plan"] and not state["metrics"]["tool_calls"] else
                    "Continue from last_observation. Choose one new useful tool, revise a falsified hypothesis, or finish when the dossier is supported. Do not repeat completed stages.")
            messages = [{"role": "system", "content": SYSTEM_PROMPT if profile["track"] == "legacy" else DISCOVERY_SYSTEM}]
            if style:
                # Separate, lower-priority system message: wording only, never tool or evidence rules.
                messages.append({"role": "system", "content": style})
            messages.append({"role": "user", "content": json.dumps(snapshot, ensure_ascii=False)})
            # A deliberately conservative UTF-8-byte estimate, not a tokenizer count.
            reserve = len(json.dumps(messages, ensure_ascii=False).encode()) + 1024 + limits["max_output_tokens"]
            if state["metrics"]["estimated_tokens_reserved"] + reserve > limits["max_total_tokens"]:
                raise TimeoutError("Estimated token budget exhausted")
            state["metrics"]["estimated_tokens_reserved"] += reserve
            state["metrics"]["policy_turns"] += 1
            if mode == "live":
                state["metrics"]["model_calls"] += 1
            if hasattr(client, "timeout"):
                client.timeout = min(120, max(0.1, tools.deadline - monotonic()))
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
                action, discarded = first_action(content)
                if discarded:
                    state["protocol_note"] = "Only the first returned action was applied. Later concatenated actions were discarded because they lacked actual tool observations. Return ONE action and stop."
                    state["metrics"]["discarded_speculative_actions"] = state["metrics"].get("discarded_speculative_actions", 0) + discarded
                    event("protocol_notice", {"message": state["protocol_note"], "discarded_actions": discarded})
                kind = action.get("action")
                if kind == "plan":
                    if state["plan"] and state["last_observation"] and state["last_observation"].get("status") in {"plan_updated", "action_error"}:
                        raise ValueError("A plan already exists. Execute a registered tool and observe its result before replanning.")
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
                    if profile["track"] != "legacy":
                        verified = any(c["certificate_verified"] for c in state["calculations"]) or any(e["certificate_verified"] for e in state["evidence"])
                        # A design may honestly state that no implemented exact kernel applies to the question.
                        no_kernel = profile["track"] == "experiment" and any(not d["calculation_ids"] for d in state["experiment_designs"])
                        state["exact_kernel_applicable"] = not no_kernel or verified
                        verified = verified or no_kernel
                        deliverable = (bool(state["experiment_designs"]) and bool(state["structure_assessments"])) if profile["track"] == "experiment" else bool(state["directions"])
                        state["status"] = "completed" if verified and deliverable else "incomplete"
                        state["delivery_scope"] = "Conditional research dossier; sample assignment, feasibility and novelty remain unresolved."
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
    state["evidence_hash"] = digest({"candidates": state["candidates"], "evidence": state["evidence"], "claim_checks": state["claim_checks"], "calculations": state["calculations"], "sources": state["sources"]})
    event("finished", {"status": state["status"], "evidence_hash": state["evidence_hash"]})
    write_json(output / "result.json", state)
    from symmetrylab.communication.workbench import render_agent_report
    for audience in ("researcher", "student", "general"):
        (output / f"report_{audience}_en.md").write_text(render_agent_report(state, audience), encoding="utf-8")
    return state
