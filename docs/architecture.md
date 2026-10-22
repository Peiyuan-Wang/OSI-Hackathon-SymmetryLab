# Architecture and Interfaces

Status: **v0.3.1 discovery preview** (2026-10-23, Asia/Shanghai). See the
[algorithm map](algorithm_flowchart.md) for the research workflows, personalization,
and attention-routed interest adaptation.

## Runtime shape

```text
CLI ─┐
    ├─> agent_core/workbench ─> model adapter ─> one bounded JSON action per turn
Web ┘                           │
                                ├─> registered research tools ─> exact verifier / SSG skill
                                ├─> bounded public-source adapters
                                ├─> scoped memory and user preference context
                                └─> database state + JSONL trace + audience reports

CLI verify/evaluate ─> verifier ─> independent certificate checker
Paper survey ─> arXiv/Crossref + local encoder/ranker/profile storage
```

## Module responsibilities

| Area | Responsibility |
|---|---|
| `agent_core` | Run state machine, research profile, action validation, budgets, observations, synthesis and optional writing pass |
| `model` | Replaceable OpenAI-compatible client plus explicitly labeled simulated offline policies |
| `tools` / `skills` | Bounded data-only operations; dispatches legacy gauge, material discovery and SSG catalog calls |
| `verifier` | Exact rational group/action checks, modular common-gauge solver, conditional orientation kernels and independent certificate checks |
| `database` | Local run persistence and read-only access to the optional SSG catalog |
| `memory` | Scoped retrieval of independently rechecked computational lessons and context-matched human preferences |
| `communication` | Deterministic audience reports, checked key findings and explicit evidence/interpretation boundaries |
| `observability` | Append-only JSONL run events and evidence hashes |
| `evaluation` | Frozen affine and discovery seed suites; labels are independent of the research model |
| `literature` | arXiv/Crossref retrieval, encoder vectors, multi-interest ranking, feedback and separate writing context |
| `web` / `desktop` | Loopback UI/API or native window; neither contains mathematical labels |

The verifier has no dependency on prompts, model outputs, or benchmark labels. Model
content is data and can request only registered tools. The SSG catalog path is selected
by application configuration, never by model-generated arguments. MCP remains a future
extension boundary.

## Research execution

`run_agent` initializes a bounded state, recalls eligible evidence, then repeats: send the
current state to the selected policy; parse only the first JSON action; validate it; run a
registered tool if requested; return the observation on the next turn. The supported
actions are `plan`, `hypothesis`, `tool`, and `finish`. Demo and live policies share the
same controller. The discovery profile selects theory or experiment contracts; an omitted
profile preserves the legacy affine workflow. Budgets, cancellation and malformed-action
limits are enforced by the controller.

The legacy `demo` command also retains a smaller `run_research` path for finite supplied
cases and two whitelisted propositions. It supports scripted, constrained live, and
evidence-checked replay modes; this is distinct from the iterative `research`/workbench
controller.

## Mathematical interfaces and evidence

- `validate_case` checks schema and supported scope; `check_group_relations` exactly
  evaluates linear, sign and affine relators before classification.
- `solve_gauge_equivalence(case, target_q=None, budget=None)` solves one shared modular
  system for all generators and returns a solution or obstruction/exhaustion evidence.
- `verify_certificate` is independent of the solver implementation. It validates input
  hashes and relations, substitutes exact witnesses, and independently checks exhaustive
  nonexistence within a separate verification budget.
- Discovery kernels calculate director invariance and collinear neutron orientation
  factors from rational Cartesian inputs. Their results remain conditional and do not
  establish material symmetry, reciprocal-lattice reflections, energy stability or
  experiment feasibility.
- `momentum_orbit` and `verify_group` operate on stored graded reciprocal SSG records;
  they do not establish a material assignment or recompute continuous specializations.

All mathematical inputs use exact integers/fraction strings. Invalid, inconsistent,
unsupported and budget-exhausted inputs remain distinct outcomes; none is silently
reclassified as a valid nontrivial case.

## Persistence and reporting

Each run writes a state snapshot, `trace.jsonl`, a frozen result, source and calculation
provenance, an evidence hash, metrics, and researcher/student/general reports. The local
web workbench owns credentials, generated run IDs, cancellation and same-origin/request
token checks. The optional writing call runs after research with no tools, receives an
immutable checked-claim ledger, and cannot change certificates; rejected output leaves the
original synthesis intact. Hashes are integrity aids, not signatures or proof of novelty.

The SSG database and user literature/profile vectors live in local data storage and are
excluded from ordinary Git tracking. The SSG integration reads its catalog read-only.
