from copy import deepcopy
import json
from pathlib import Path
import pytest
from symmetrylab.agent_core.research_loop import run_research
from symmetrylab.communication.render import render_report, audit_result, AUDIENCES
from symmetrylab.evaluation.benchmark import load_suite, evaluate
from symmetrylab.schemas import read_json
from symmetrylab.verifier.counterexample import find_counterexample
from symmetrylab.model.client import OpenAICompatibleClient
from symmetrylab.cli import main

ROOT = Path(__file__).resolve().parents[2]


def inputs():
    return [c for c, _ in load_suite(ROOT / "benchmarks/manifest.json", "golden")]


def test_scripted_research_replay_and_shared_reports(tmp_path):
    result = run_research(inputs(), tmp_path / "first")
    assert result["hypothesis_status"] == "Counterexample found"
    assert result["counterexample"] == "T01"
    assert result["lessons"][0]["evidence_status"] == "certificate_verified"
    assert result["metrics"]["model_calls"] == 0
    for audience in AUDIENCES:
        text = render_report(result, audience)
        assert result["evidence_hash"] in text and "toy" in text
        assert text.startswith("# SymmetryLab Research Report")
        assert (tmp_path / "first" / f"report_{audience}_en.md").read_text(encoding='utf-8') == text
    replay = run_research([], tmp_path / "replay", mode="replay", source=tmp_path / "first")
    assert replay == result
    assert read_json(tmp_path / "replay/replay.json")["mode"] == "replay"
    for audience in AUDIENCES:
        assert (tmp_path / "replay" / f"report_{audience}_en.md").is_file()
    with pytest.raises(ValueError, match="empty"):
        run_research(inputs(), tmp_path / "first")


def test_report_rejects_changed_evidence(tmp_path):
    result = run_research(inputs(), tmp_path / "run")
    result["evidence"][0]["result"]["theta"] = ["0", "0"]
    with pytest.raises(ValueError, match="hash"):
        audit_result(result)


def test_joint_hypothesis_and_finite_scope():
    result = find_counterexample("individual_implies_joint", inputs())
    assert result["counterexample"] == "T05"
    none = find_counterexample("nonzero_q_implies_nontrivial", inputs()[1:2])
    assert none["counterexample"] is None and "finite" in none["status"]
    limited = find_counterexample("individual_implies_joint", inputs(), max_cases=1)
    assert limited["status"] == "budget_exceeded"


class FakeClient:
    def __init__(self):
        self.requests = []

    def complete(self, messages, max_tokens):
        self.requests.append(messages)
        answer = {"predicate": "nonzero_q_implies_nontrivial"} if len(self.requests) == 1 else {"criterion": "common_gauge_image"}
        return {"content": json.dumps(answer), "usage": {"total_tokens": 50}}


def test_live_control_flow_with_mock_only(tmp_path):
    client = FakeClient()
    result = run_research(inputs(), tmp_path / "mock", "live", client=client)
    assert result["metrics"]["model_calls"] == 2
    assert result["metrics"]["provider_reported_tokens"] == 100
    assert result["mode"] == "live"  # mocked test, never shipped as a real online run


def test_token_budget_stops_before_request(tmp_path):
    client = FakeClient()
    with pytest.raises(RuntimeError, match="budget"):
        run_research(inputs(), tmp_path / "limited", "live", {"max_total_tokens": 1}, client)
    assert not client.requests
    assert '"FAILED"' in (tmp_path / "limited/trace.jsonl").read_text(encoding='utf-8')


def test_invalid_model_predicate_does_not_execute(tmp_path):
    class BadClient:
        def complete(self, messages, max_tokens):
            return {"content": '{"predicate":"run_shell"}'}
    with pytest.raises(ValueError, match="whitelist"):
        run_research(inputs(), tmp_path / "bad", "live", client=BadClient())


def test_private_inputs_blocked_before_model_call(tmp_path):
    cases = inputs()
    cases[0]["privacy"] = "private_research"
    client = FakeClient()
    with pytest.raises(ValueError, match="public_toy"):
        run_research(cases, tmp_path / "private", "live", client=client)
    assert not client.requests


def test_adapter_configuration_fails_closed(monkeypatch):
    config = {"base_url": "http://example.com/v1", "model": "test"}
    with pytest.raises(ValueError, match="HTTPS"):
        OpenAICompatibleClient(config)
    config["base_url"] = "https://example.com/v1"
    monkeypatch.delenv("SYMMETRYLAB_API_KEY", raising=False)
    with pytest.raises(ValueError, match="No API key saved"):
        OpenAICompatibleClient(config)


def test_cli_and_evaluation(tmp_path, capsys):
    assert main(["verify", str(ROOT / "benchmarks/golden/T01.json")]) == 0
    assert main(["verify", str(ROOT / "benchmarks/golden/T03.json")]) == 2
    metrics = evaluate(ROOT / "benchmarks/manifest.json", tmp_path / "eval")
    assert metrics["total"] == metrics["correct"] == 30
    assert metrics["certificates_verified"] == 27
    assert metrics["llm_ablation_status"] == "not_run"
