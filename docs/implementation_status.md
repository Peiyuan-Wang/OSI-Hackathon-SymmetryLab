# Implementation Status

Current working tree: **v0.3 discovery preview**, 2026-10-22 (Asia/Shanghai). The installed package metadata remains 0.2.0; this preview has not been packaged or published as a release.

## Implemented in this revision

| Area | Current behavior |
|---|---|
| Theory workspace | Original layout retained at `/`; paper/DOI/excerpt input, interest keywords, preference corrections, evidence-linked taste hypotheses and two-direction comparison |
| Experimental workspace | Matching blue layout at `/experiment`; default L10 MnPt Neel-axis goal; conditions and instrument inputs |
| Source layer | Bounded COD metadata and Crossref metadata/DOI adapters, provenance, response hashes and failure records; curated primary-source MnPt context |
| Exact experimental kernels | Rational Cartesian director invariance and collinear neutron orientation factors, independent checks, sign/geometry/scale/domain degeneracies |
| Discovery controller | Model-driven conditional structure assessment, calculations, directions and experiment-design tools; legacy affine tools preserved |
| Reports | Source scope, unverified structure interpretation, exact conditional calculations, proposed directions, controls, predictions, falsifiers and missing requirements |
| Personal taste | Exact-excerpt provenance, explicit researcher corrections, pairwise preference feedback saved separately and scoped to selected-paper context |
| Inference-time improvement | Current-run feedback plus independently rechecked orientation/gauge counterexample recall; demo/live separation; no changes to verifier or labels |
| Provider compatibility | Application User-Agent; bounded long-request handling; concatenated JSON responses apply only the first action and discard speculative later actions |
| Benchmark assets | 12 executable public seed cases; unlabelled preference packet; proposed 48-packet collection and matched-budget ablations |

## Checks completed

- Full regression suite: **87 passed**, including local HTTP navigation, origin/token protection, two workspaces, human preference endpoint and speculative-action rejection.
- Python compilation, JavaScript syntax check and Git whitespace check passed.
- New deterministic discovery seed suite: **12/12 correct**, zero model calls. This is not a taste or improvement evaluation.
- Both offline workflows complete with actual exact tools. MnPt produces three conditional calculations and an experiment-design record; theory produces two proposals and a provisional taste profile when context is supplied.
- Browser: both current workspaces completed new offline runs. The MnPt run produced three checked calculations and one design; theory produced two proposals, keyword-linked preference provenance and a feedback form. Screenshots are saved in the workspace outputs folder.
- Crossref live search returned five MnPt-related records. COD did not return a valid live structure result in this environment; failures are retained as unavailable, not interpreted physically.
- The user's explicitly supplied local API configuration successfully returned a real small response from the requested `gpt-6.1-sol` service. No key is stored in repository files.
- The first full live run timed out before a tool call. A diagnostic response arrived after approximately 77 seconds with multiple concatenated actions; this motivated the independently tested single-action recovery. A subsequent live run was interrupted after two calculations. The final live acceptance run `73d8f667149b466ba8221343ebdb5c67` failed on its seventh model request after 266.92 seconds: five tool calls, nine source records (four curated and five retrieved), one structure assessment and one independently checked calculation were preserved. No experiment-design record or final synthesis was produced. End-to-end live acceptance remains **not passed**; the failure is a connection/timeout error, not evidence of an invalid API key or a physical conclusion.

- Malformed structure queries now receive repair instructions distinct from source outages. The evidence notebook displays failed retrievals and unresolved structure assessments.
- Preference feedback requires a completed dossier. With no selected papers, later recall also requires matching keywords.
- Repository-visible files were checked against the supplied API key: zero matches. Local provider diagnostics and evaluation outputs are ignored by Git.

## Scientific and implementation limits

This is a conditional research prototype. No sample-specific MnPt magnetic structure, magnetic propagation vector, MSG/SSG, accessible reflection set, energy minimum, calibrated intensity, XMLD spectrum, growth recipe or experimental feasibility has been established. Chemical symmetry does not determine the sample Neel axis. The exact kernels establish only their specified mathematical consequences.

Full-text/PDF paper ingestion, author disambiguation, trained personal preference models, calibrated direction ranking, held-out expert benchmarks, statistical RSI gains and RLVR/GRPO training remain unimplemented. The 48-packet benchmark is a collection protocol, not completed data. The sidebar's real-model mode is distinct from fixed offline walkthroughs.

See [Discovery benchmark and RSI](design/discovery_benchmark_rsi.md) for the full definitions, source references, experiments and priorities. Local credentials and runtime records remain outside tracked source files. This revision has not been committed or pushed.

---

# Historical v0.2 checkpoint

Version: 0.2.0. Validation date: 2026-10-22 (Asia/Shanghai).

## Implemented

| Area | Evidence |
|---|---|
| Exact verifier | Canonical C2 / C4 / C2xC2 presentations, affine relations, rational gauge solver, independent certificates |
| Model-driven controller | Model-generated plans, hypotheses and candidates; observed tool feedback; current-run counterexample memory; bounded iteration |
| Six research tools | Candidate registration, relation checking, gauge solving, gauge comparison, finite shift scanning, executable claim tests |
| Model connection | Chat Completions and Responses adapters; CC Switch loopback preset; environment-based custom authentication; JSON/SSE parsing |
| English graphical workbench | Question input, connection settings and probe, run/stop, plan/activity, candidate matrices, certificates, history, audience reports and downloads |
| Persistence | Atomic snapshots, JSONL traces, final JSON and three Markdown reports; interrupted runs identified on restart |
| Legacy CLI | Verify, deterministic benchmark, controlled demo and replay remain available |
| Packaging | Editable installation upgraded to 0.2.0; wheel built and checked for all three static UI assets |

## Validation

Executed in the project's isolated Python 3.12.7 environment:

- Full test suite: **66 passed**. Includes actual loopback HTTP server integration.
- Source compilation: passed.
- Dependency consistency: no broken requirements.
- Deterministic benchmark: **30/30** correct labels, **27/27** valid mathematical certificates, zero model calls.
- Offline iterative CLI: completed with 8 policy turns, 4 tool calls and 2 certified instances.
- Actual browser interaction: started the offline run, observed completion, counterexample feedback, hypothesis revision and exact certificates; switched report audience and inspected CC Switch connection fields.
- Wheel: built successfully; HTML, CSS and JavaScript assets present.

Protocol tests use simulated HTTP responses, including Responses JSON/SSE, placeholder authentication, loopback proxy bypass and remote-error sanitization. An adaptive model double repairs an invalid candidate based on actual tool feedback and then solves it. Budget, cancellation, unsupported tool, incomplete finish, finite scans, mismatched comparisons, relation inconsistency, origin/token protection and restart recovery are tested.

The existing mathematical tests include 400 one-dimensional systems checked against a complete grid, gauge/basis/integer-representative transformations, exhaustive-fallback cases and certificate tampering. These are correctness checks within the supported toy scope, not proof of a discovery advantage.

## Real-model validation boundary

No real model response has been validated in this environment. CC Switch 3.20.3 is installed, but no local listener on port 15721 was running at the check. The workbench needs Codex routing enabled and a provider-supported model ID before a real connection test. The newer upstream conversion guide applies to 3.20.4 and later; older-version format conversion is unverified here.

## Remaining research work

- Real provider evaluation and equal-budget A/B/C/D ablations; held-out benchmarks.
- Formal parsing and proof of arbitrary natural-language hypotheses.
- Cross-run memory retrieval and automatic continuation of interrupted runs.
- MCP and Mathematica integration; general group presentations and physical SSG inputs.
- Smith normal form with transformations, complete solution-set parameterization and cohomology classification.
- Novelty assessment, real material predictions and RLVR/GRPO weight training.

The graphical workflow and model orchestration are implemented. An autonomous discovery system that outperforms baselines has not been established. Runtime data remain ignored by Git.
