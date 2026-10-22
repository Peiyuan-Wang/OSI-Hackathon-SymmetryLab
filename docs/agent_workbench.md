# Model-Driven Research Workbench

## Design

Version 0.2 adds an iterative controller and a local browser workbench. The existing deterministic verifier remains the mathematical boundary.

The model receives a research question, explicit tool contracts, a compact state snapshot, and the previous tool observation. It returns one JSON action per turn: update a plan, propose a hypothesis, invoke a tool, or finish. Candidate matrices and shifts come from the model's tool arguments, not from Golden labels. The next model turn receives actual results and can repair or revise its choices.

Actions are data. The legacy controller uses registered tools: register_candidate, check_relations, solve_gauge, compare_gauge, scan_shifts, and test_claim. No shell, Python, filesystem, or arbitrary network tools are exposed. The v0.3 extension below adds bounded metadata retrieval and discovery tools. Free-form hypotheses and final synthesis remain model proposals; only certified tool results are verified facts. Formal claim checks use named executable predicates and list their finite domain explicitly.

Budgets bound model requests, tool calls, candidates, output tokens, total estimated tokens, and wall time. Cancellation is cooperative between requests and tools. A network request already in progress may finish before cancellation takes effect. Invalid actions return structured feedback; repeated protocol errors terminate the run. Successful completion requires at least one verified mathematical result.

## Model connection

Use an OpenAI-compatible Chat Completions or Responses endpoint. Configure the Base URL (normally ending in /v1), model ID, protocol and API key on the **Connection** page. The key is saved in a user-only local file and is never sent back to the interface or written to run records, traces or reports; CLI runs may instead use the SYMMETRYLAB_API_KEY environment variable. The controller uses JSON actions in ordinary messages, so native provider function-calling support is not required.

Demo mode uses a clearly identified simulated policy with the same tool execution path. Its actual mathematics is computed locally; it is not evidence of a live LLM's capabilities. The simulator does not read benchmark answers.

## Local UI and storage

Bind only to 127.0.0.1. Browser mutations require a per-server request token and same-origin checks. The UI uses local assets and renders model text as text, not HTML. There is one active run at a time. Each run has a generated ID and its own folder under data/workbench; URLs cannot name arbitrary filesystem paths.

The interface supports connection settings, a research question, live/demo selection, progress, cancellation, plans, hypotheses, tool observations, candidate details, exact evidence, three English report views, and report/JSON downloads. API keys stay in server environment variables. Persist state snapshots and event logs so completed and interrupted runs can be inspected after a server restart; automatic continuation of an interrupted run is not yet supported.

## Validation

Test adaptive multi-turn behavior with a scripted model double that repairs an invalid candidate after observing tool feedback. Test budgets, unsupported actions, certificate checks, candidate limits, cancellation, missing credentials, and HTML injection handling. Exercise actual local HTTP endpoints and inspect the UI in a browser. Real custom-provider validation requires a supplied endpoint/model and a locally configured key; simulated tests must not be reported as real API success.

## Implementation map

- `agent_core/workbench.py`: `run_agent(goal, output, mode, config, client, cancelled, on_update)` and validated budgets.
- `agent_core/prompt.py`: actual packaged JSON-action prompt and full tool contracts.
- `tools/research.py`: six registered tools; no provider or browser dependency.
- `model/client.py`: two protocols, saved or environment API key, no redirects, bounded responses, JSON/SSE response parsing.
- `model/simulated.py`: clearly labeled offline policy that reacts to current state.
- `database/workbench.py`: generated IDs, constrained paths, persisted snapshots and history.
- `web/server.py`: loopback HTTP, per-server request token, origin checks, one worker, cancellation and download endpoints.
- `communication/workbench.py`: audience guide plus independently rechecked instance evidence.

Defaults: 24 model turns, 24 tool calls, 40 candidates, 1,600 output tokens per response, 180,000 conservatively reserved estimated tokens, and 240 seconds. The token estimate counts UTF-8 bytes plus request overhead; reported provider usage is tracked separately and may be missing. Time limits are cooperative: network operations have a timeout and mathematical checks finish at checkpoints. No claims of a hard real-time deadline are made.

Supported actions are `plan`, `hypothesis`, `tool`, `finish`. Tool schemas live in the prompt and are validated again by the Python functions. `finish` without a certified instance yields `incomplete`. Three consecutive malformed actions yield `failed`. Invalid mathematical candidates yield observations for the next policy turn. Finite scans record their denominator, domain size and truncation. Evidence hashes bind candidates, exact results and claim-check records; they are integrity aids, not signatures or proofs of novelty.

The run stores `state.json`, `trace.jsonl`, `result.json`, and three `_en.md` reports. Model free-form output is always labeled unverified. Current-run lessons feed back into the model state. Persistent history supports inspection. The v0.3 extension adds scoped cross-run retrieval; self-modifying source, weight updates and automatic continuation remain unimplemented.

## v0.3 discovery extension

See [Discovery benchmark and RSI](design/discovery_benchmark_rsi.md). New requests carry a validated `research_profile` with `track=theory|experiment`, material/conditions/instruments, keywords/papers/taste_notes and a lesson-reuse flag. Omitted profiles preserve the legacy API and CLI. `/experiment` reuses the original layout with a blue palette. Public cross-site top-level navigation is permitted for the two HTML pages after Host/Origin checks; API reads and mutations remain protected.

New data-only tools retrieve public metadata, record structure interpretations, calculate rational orientation factors, check conditional director invariance, propose directions, design experiments and infer excerpt-linked taste. New records have separate source, calculation, preference and proposal statuses. Human preference feedback is stored in a separate JSONL file and cannot change exact results. A completed discovery run means a conditional dossier, not verified material realization.

CLI examples (choose a new output directory each time):

```bash
.venv/bin/python -m symmetrylab research --mode demo --config config/experiment.example.json --goal "Determine the Neel-axis orientation of L10 MnPt" --output data/mnpt-demo-001
.venv/bin/python -m symmetrylab research --mode demo --config config/theory.example.json --goal "Explore minimal symmetry mechanisms" --output data/theory-demo-001
```

In live mode, set the model ID and authentication appropriately in a local copy. The `serve --config` argument accepts only public connection settings; the web form supplies the research profile separately. The CLI `research --config` argument accepts both connection and research-profile settings.

The local user-specific launcher outside the repository reads the explicitly supplied desktop credential text file into the server process environment. It is not packaged or committed. For a portable installation use the documented environment-variable workflow.

Malformed source queries receive repairable `invalid_query` feedback before network access. Retrieval failures remain `unavailable` and do not imply that a structure is absent. Both appear in the evidence notebook. Pairwise feedback is accepted only for completed dossiers; keyword-only profiles also require matching keywords for later recall.
