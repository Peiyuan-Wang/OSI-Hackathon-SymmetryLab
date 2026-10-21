# Architecture and Interfaces

Status: v0.2 includes a graphical workbench and an iterative model controller. Protocol adapters and adaptive control pass mock tests; no real provider request has yet been validated.

```text
CLI → agent_core → model protocol / verifier / memory
                 → observability → data/<run_id>/trace.jsonl
                 → communication → Three audience reports
CLI → evaluation → verifier → Independent certificate check
```

The module boundaries follow Newspaper. The model module provides replaceable OpenAI-compatible HTTP communication. The verifier has no dependency on models, prompts, or experimental labels. Registered research tools and local run persistence are implemented. MCP remains an extension boundary.

`validate_case` and `check_group_relations` return input and relation statuses. `solve_gauge_equivalence(case, target_q=None, budget=None)` returns a classification and evidence. Supply target_q as a complete list of vectors in operations order; the target action is also checked for validity.

`verify_certificate` does not call the main solver. It directly checks fractional solutions and integer obstructions. Exhaustive evidence is cross-checked using an independent complete grid whose denominator bound comes from integer minors. Exceeding the verification budget returns false.

`find_counterexample` supports two allowlisted propositions over an explicitly supplied finite domain. `run_research` records state transitions, input hashes, tool results, lessons, and reports. Template-based revision is a controlled workflow; an empirical learning benefit has not been established.

Run artifacts are written to a new `data/<run_id>/` directory. Nonempty output directories are rejected. Failures produce a FAILED event. Completed results can be replayed, but automatic resumption from an intermediate model call is not implemented.

All newly generated text is English. Reports use the `_en.md` suffix. A legacy result's canonical executable predicate can be rendered in English without modifying its frozen payload or evidence hash.

## Workbench path

```text
Browser → loopback web server → agent_core/workbench
                              → model/client → CC Switch or custom service
                              → tools/research → verifier → independent certificate
                              → database → state, trace, reports
```

The model emits one JSON action per turn. It receives tool observations and counterexample lessons before selecting another action. Both the simulated policy and live adapter use the same controller and tools. The server owns credentials, generated run identifiers, cancellation and same-origin checks. See [agent workbench](agent_workbench.md).
