# Implementation Status

## Material-explorer integration, 2026-10-22

The additive `/materials` page includes 50 unranked research directions, explicit unknown SG/MSG/SSG fields, an exact Cartesian linear AHE constraint checker with checked certificates, offline trace and JSON export. Its optional model-proposal endpoint uses the existing CC Switch/custom-provider adapter and keeps model text unverified. The original workbench is preserved. Material/SSG lookup and actual literature retrieval remain unconnected adapters.

The teammate's delivery was based on commit `b6a38414e1ff4e481e3494753668af4138043d46`. All 106 source-file hashes matched its manifest, and the 15 changed paths were imported as a separate commit. On the receiving macOS Python 3.12.7 environment, the combined suite passes **88 tests**, source compilation and both JavaScript syntax checks pass, and dependency checks report no broken requirements. The deterministic benchmark remains **30/30** correct labels with **27/27** valid certificates and zero model calls. The relay changes identify requests as `SymmetryLab/0.2` and use a 60-second timeout; adapter tests check these request properties.

The sender reports a successful short live Responses request against `https://api.huanling.icu/v1` with requested model `gpt-6.1-sol`. This result was not independently repeated during integration, and it does not establish that CC Switch forwarding or full model-driven research succeeds on the receiving machine. No credentials or sender-built wheel were imported. See `material_explorer.md` for the setup and scientific limits.

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

## Original workbench validation checkpoint

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

## Original real-model validation boundary

At the original workbench checkpoint, no real model response had been validated in this environment. CC Switch 3.20.3 was installed, but no local listener on port 15721 was running at that check. Subsequent troubleshooting confirmed a running local route but observed an upstream Cloudflare 403. The teammate's later request-header change has not been independently validated against that route during integration. The newer upstream conversion guide applies to 3.20.4 and later; older-version format conversion remains unverified here.

## Remaining research work

- Real provider evaluation and equal-budget A/B/C/D ablations; held-out benchmarks.
- Formal parsing and proof of arbitrary natural-language hypotheses.
- Cross-run memory retrieval and automatic continuation of interrupted runs.
- MCP and Mathematica integration; general group presentations and physical SSG inputs.
- Smith normal form with transformations, complete solution-set parameterization and cohomology classification.
- Novelty assessment, real material predictions and RLVR/GRPO weight training.

The graphical workflow and model orchestration are implemented. An autonomous discovery system that outperforms baselines has not been established. Runtime data remain ignored by Git.
