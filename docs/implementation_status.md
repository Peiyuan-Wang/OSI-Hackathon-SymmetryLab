# Implementation Status

Current version: **0.3.1 discovery preview**, 2026-10-23 (Asia/Shanghai). Release builds are produced by the `v*` tag workflow after both platform packages pass their SSG-required smoke checks.

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

- Full regression suite: **108 passed**, including local HTTP navigation, origin/token protection, two workspaces, human preference endpoint and speculative-action rejection.
- Python compilation, JavaScript syntax check and Git whitespace check passed.
- New deterministic discovery seed suite: **12/12 correct**, zero model calls. This is not a taste or improvement evaluation.
- Both offline workflows complete with actual exact tools. MnPt produces four conditional calculations (three when a lesson is recalled) and an experiment-design record; theory produces two certified instances, two proposals and a provisional taste profile when context is supplied.
- Browser: both current workspaces completed new offline runs. The MnPt run produced three checked calculations and one design; theory produced two proposals, keyword-linked preference provenance and a feedback form. Screenshots are saved in the workspace outputs folder.
- Crossref live search returned five MnPt-related records. COD did not return a valid live structure result in this environment; failures are retained as unavailable, not interpreted physically.
- The user's explicitly supplied local API configuration successfully returned a real small response from the requested `gpt-6.1-sol` service. No key is stored in repository files.
- The first full live run timed out before a tool call. A diagnostic response arrived after approximately 77 seconds with multiple concatenated actions; this motivated the independently tested single-action recovery. A subsequent live run was interrupted after two calculations. The final live acceptance run `73d8f667149b466ba8221343ebdb5c67` failed on its seventh model request after 266.92 seconds: five tool calls, nine source records (four curated and five retrieved), one structure assessment and one independently checked calculation were preserved. No experiment-design record or final synthesis was produced. End-to-end live acceptance remains **not passed**; the failure is a connection/timeout error, not evidence of an invalid API key or a physical conclusion.

- Malformed structure queries now receive repair instructions distinct from source outages. The evidence notebook displays failed retrievals and unresolved structure assessments.
- Preference feedback requires a completed dossier. With no selected papers, later recall also requires matching keywords.
- Repository-visible files were checked against the supplied API key: zero matches. Local provider diagnostics and evaluation outputs are ignored by Git.

## Review fixes (2026-10-22)

- Reports open with mechanically derived **Key findings** and **Still open**; JSON inputs are one line (Researcher only); the nested v0.2 report inside theory dossiers was removed.
- Audiences now differ in content: Researcher (full tables, inputs, controls, requirements), Physics student (glossary, tables without raw inputs), General reader (findings, plain-language meaning, predictions).
- The workbench renders reports as formatted Markdown, shows offline runs as "Offline" instead of "0 model calls", reports checks as passed/total, and only shows limitation banners for runs that did not complete.
- The theory walkthrough now states its claim, refutes it (C001), contrasts a certified obstruction (C002) and builds directions on both; the default question matches.
- The MnPt walkthrough compares C4z and C2z domain assumptions (V001/V002) instead of a single assumed C4 check.
- Recalled lessons change the scripted plan: the theory run starts from the revised claim; the experiment run skips the known degenerate c-only probe.
- Decorative hero graphic, static pipeline strip, duplicate sidebar buttons and footer were removed; each tool call shows its specific purpose.

## Fixes after the live MnPt TMR run (2026-10-22)

- Lessons are recalled only from runs with the same material and an overlapping question (token overlap ≥ 0.3); a Neel-axis lesson no longer reaches a TMR question. A sidebar **Clear history & memory** button deletes one workspace's runs, lessons and preferences after confirmation (`POST /api/runs/clear`, token-protected, refused while a run is active).
- The prompt no longer prefers neutron geometry. Exact kernels are used only when they answer the question; `design_experiment` accepts `calculation_ids: []`, and the report then states that no implemented kernel applies.
- New `arxiv` source kind (arXiv API); arXiv DOIs (10.48550/…) resolve through arXiv instead of Crossref, which returns 404 for them. Crossref searches request journal/posted/proceedings records, so supporting-information files (`.s001`) are excluded. Every retrieved record carries `mentions_material`; off-topic records are collapsed in reports and the UI.
- The curated MnPt packet now includes arXiv:2510.04184 (spin polarization in PT-symmetric antiferromagnets including L10-MnPt).
- Reports open with the direct answer; the model is asked to answer in the language of the question.

## Paper survey (2026-10-22)

- New `/papers` workspace: arXiv retrieval, optional PhysBERT or lexicon embeddings, anchored multi-interest ranking with reversible feedback, and emerging-interest signals. Personalization now adds query-source coverage, explicit research intent, evidence-linked historical facets, independent writing selections, corpus freshness checks and a separate post-research writing pass. See [paper_survey.md](paper_survey.md). Hybrid ranking weights and writing quality remain uncalibrated; regression success is not a user-quality benchmark.
- Verified: 103 tests; end-to-end browser run against live arXiv with PhysBERT (103 candidates, votes re-rank, profile built). Not verified: effect of the voice profile on a real model's prose.

## Desktop app and connection page (2026-10-22)

- Native window via pywebview 6.2.1 around the unchanged interface; PyInstaller spec and `scripts/build_mac_app.sh` (dependencies, tests, PhysBERT, `.app`). Per-user data in `~/Library/Application Support/SymmetryLab`.
- CC Switch support removed. New **Connection** page: Base URL, model ID, protocol and API key, saved in a 0600 file; the key is never returned to the interface or written to runs. The research page shows a one-line connection status.
- Verified: 108 tests; frozen Linux builds (lite and with PyTorch) driven end to end. Not verified: the macOS `.app` (must be built on the Mac).

## Scientific and implementation limits

This is a conditional research prototype. No sample-specific MnPt magnetic structure, magnetic propagation vector, MSG/SSG, accessible reflection set, energy minimum, calibrated intensity, XMLD spectrum, growth recipe or experimental feasibility has been established. Chemical symmetry does not determine the sample Neel axis. The exact kernels establish only their specified mathematical consequences.

Full-text/PDF paper ingestion, author disambiguation, trained personal preference models, calibrated direction ranking, held-out expert benchmarks, statistical RSI gains and RLVR/GRPO training remain unimplemented. The 48-packet benchmark is a collection protocol, not completed data. The sidebar's real-model mode is distinct from fixed offline walkthroughs.

See [Discovery benchmark and RSI](design/discovery_benchmark_rsi.md) for the full definitions, source references, experiments and priorities. Local credentials and runtime records remain outside tracked source files.

The v0.2 checkpoint is archived in [reports/v0.2_checkpoint.md](reports/v0.2_checkpoint.md).

## SSG skill integration (2026-10-23)

- Original schema-3 SQLite catalog (67,475 records) and paclet copied locally with matching SHA-256 hashes; data remains Git-ignored.
- Model-discoverable skill supports metadata, filtered/paginated lookup, reciprocal/O(3)/MG sections, exact momentum orbits and graded generator-closure checks.
- Source IDs, record hashes and calculation results are retained in the research dossier.
- Removed the fixed Verification scope UI block; per-result assumptions remain explicit.
- SQLite quick_check passed; all 26 deterministic sampled group checks passed. This is not exhaustive re-verification.
- Wolfram paclet execution, arbitrary Hamiltonian calculation and continuous-parameter recomputation are not yet exposed.
- See `docs/ssg_skill.md` and `scripts/check_ssg_catalog.py`.
