# Counterexample-Driven Research and Reporting

See the README demo commands. Inputs are limited to public toys. Outputs include a trace, frozen result, lessons, metrics, and three English reports.

- **scripted**: start from an explicitly preset false proposition; deterministically search for an actual counterexample, verify it, record a lesson, and apply the common gauge criterion to the remaining examples. No API calls.
- **live**: use an HTTPS OpenAI-compatible provider with an environment-variable key. The model chooses one of two propositions and selects a revised criterion in a constrained format after receiving exact evidence. Open-ended scientific hypothesis generation is not implemented.
- **replay**: require an existing completed result; recheck its evidence and hash, then render it. Preserve the original result identity and record the source in replay.json.

Defaults are 30 cases, 180 seconds, 6 model requests, a 12,000-token total budget, and at most 600 output tokens per response. Before a request, reserve the UTF-8 byte length of its input plus 1,024 framing units and the output allowance as a conservative estimate. Record provider-reported token usage separately. This does not guarantee a monetary billing cap across providers. Unknown prices are null. The wall-clock budget controls tools and requests; individual exact matrix operations and final report auditing may add a small amount of overhead.

Model failures, invalid JSON, incomplete configuration, and exhausted budgets stop the run and retain a FAILED event. They do not produce a simulated successful online result. Lessons are derived from checkable counterexamples and retain the proposition, scope, certificate, failure category, and strategy. Only lessons from the current run are used; cross-run retrieval and weight updates are not implemented.

The researcher/student/general views are rendered from one frozen result and share a result ID and evidence_hash. Audit the hash and mathematical certificates before rendering. Passing finite tests does not promote a conjecture to a general proof. Templates control the report text; free-form LLM rewriting is not implemented.

The renderer defaults to `language="en"` and supports English only. New report files are `report_<audience>_en.md`. Replaying an older-language result renders its known executable predicate in English while preserving the frozen source record and hash.

## v0.2 iterative research

The above describes the retained controlled `demo` workflow. For model-driven candidate construction and iterative tools, use `research --mode live` or `serve`. See [agent workbench](agent_workbench.md) for the new controller, actions, tools, limits, data flow and evidence boundaries. Free-form model hypotheses are distinct from the two executable claim predicates.
