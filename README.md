# SymmetryLab

## Material explorer extension (local handoff)

Open **http://127.0.0.1:8787/materials** after starting the server. The original mathematics workbench remains at `/`. The extension adds 50 research-direction entries, material/phase inputs, an exact linear AHE check for supplied Cartesian point-group operations, explicit missing-data states, and an optional model-planning connection through **CC Switch or a custom compatible API**. No material-to-SSG database or live literature retrieval is connected. See [Material Explorer handoff](docs/material_explorer.md) for model configuration, scientific limits, adapter contracts and the 88-test validation checkpoint.

**A Verifiable Self-Improving Agent for Condensed Matter Theory**

SymmetryLab is an initial research-agent implementation for a precise question: given rational momentum shifts that satisfy the group relations, can one common change of momentum origin remove the shifts of every generator?

```text
Testable conjecture → Exact computation → Verified counterexample
                   → Evidence-backed lesson → Revision → Scientific report
```

Version **0.2.0** adds an English graphical workbench, model-driven planning and candidate generation, iterative mathematical tools, and a CC Switch connection preset. It includes offline demonstrations, exact certificates, replay, audience reports, and a benchmark. Physical materials and SSG realizations have not been validated, and no reinforcement-learning training has been performed.

## Installation

Run these commands from the repository root. In PyCharm, select the project's `.venv` interpreter. Python >=3.11 is required; the current implementation has been tested on Python 3.12.7.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`. Dependencies come from public Python package sources. Offline verification and demonstrations require neither a GPU nor an API key.

## Open the graphical workbench

```bash
.venv/bin/python -m symmetrylab serve
```

Open **http://127.0.0.1:8787**. Select **Offline demonstration**, then **Start research** to try the complete loop without a key. This mode uses a simulated policy and real exact mathematics; it is explicitly labeled throughout the interface.

The workbench displays the evolving plan, hypotheses, tool calls, candidate matrices, exact certificates and counterexample memory. Switch the report audience or download Markdown and evidence JSON. Completed runs remain in local history. **Stop run** requests cooperative cancellation; an in-flight model request may take up to its network timeout to return. Keep the terminal running; Ctrl+C stops the server.

### Connect through CC Switch

1. In CC Switch, configure a provider under **Codex** and enable its **local routing** service.
2. In the workbench, expand **Model connection** and choose **CC Switch local routing**.
3. Keep Base URL `http://127.0.0.1:15721/v1` (or your configured loopback address), choose **Responses**, and enter a model ID supported by your provider.
4. Click **Test connection**. After it succeeds, select **Live model research** and start a run.

CC Switch injects the upstream credential. SymmetryLab sends a local placeholder and never reads CC Switch's database or Codex authentication files. Switching a provider does not guarantee the same model ID remains available; update the field when needed. See [connection details and troubleshooting](docs/cc_switch.md).

For a direct custom provider, select **Custom OpenAI-compatible service**, enter its Base URL/model, choose **Chat Completions** or **Responses**, and set `SYMMETRYLAB_API_KEY` in the environment used to start the server. The interface accepts an environment-variable name, never the key itself.

**Validation boundary:** protocol adapters and adaptive behavior pass simulated-service tests. A real provider has not yet been validated on this machine; the local CC Switch listener was not running at the validation checkpoint.

## Verify a problem

```bash
.venv/bin/python -m symmetrylab.cli verify benchmarks/golden/T01.json
```

The verifier checks the input and group relations, solves for a common theta, and independently checks the certificate. JSON output includes the classification, certificate, input hash, and certificate-verification result. A valid nontrivial classification is a successful determination. Invalid input, exhausted budgets, or an unverified certificate return exit code 2.

The criterion is

\[
(R_g-s_g I)\theta=q_g\pmod{\mathbb Z^d}\qquad\text{for every generator }g.
\]

The abstract affine convention is F_g(k)=s_g R_g k+s_g q_g, with k'=k+theta. See [Mathematical conventions](docs/mathematical_conventions.md) for definitions and physical scope. A nonzero q does not by itself establish gauge nontriviality.

## Run the offline research demonstration

```bash
.venv/bin/python -m symmetrylab.cli demo --mode scripted --output data/demo-en-v0.1
.venv/bin/python -m symmetrylab.cli demo --mode replay --source data/demo-en-v0.1 --output data/replay-en-v0.1
```

`scripted` starts from an explicitly preset false conjecture, calls the verifier to find an actual counterexample, and records the resulting lesson. `replay` requires an existing completed result. Use a new output directory for each run; existing research records are never overwritten.

Open `report_researcher_en.md`, `report_student_en.md`, and `report_general_en.md` in the output directory. All three reports share a result ID and evidence hash. The local evidence is saved in `trace.jsonl`, `result.json`, `memory.json`, and `metrics.json`.

Use `--predicate individual_implies_joint` to demonstrate why individual solvability does not imply joint solvability.

## Model-driven research from the CLI

```bash
# Offline policy exercising the same tools and state machine
.venv/bin/python -m symmetrylab research --mode demo --goal "Test whether nonzero shifts imply gauge nontriviality" --output data/research-demo

# Edit the model ID in a copy of config/cc-switch.example.json first
.venv/bin/python -m symmetrylab research --mode live --config config/cc-switch.example.json --goal "Explore valid C2 actions and find a gauge counterexample" --output data/research-live
```

In live research, the model proposes a plan, constructs candidate matrices and shifts, selects registered tools, observes their results, and revises its hypotheses. It has no shell or arbitrary code-execution access. The controller imposes call, candidate, time and token-estimate budgets. Free-form summaries stay unverified; independent exact certificates support instance facts. Read [the workbench design](docs/agent_workbench.md) for contracts and limits.

The older `demo --mode live` command remains a constrained two-decision workflow over supplied benchmark inputs. Use `research --mode live` or the graphical workbench for candidate generation and iterative planning.

## Tests and benchmark

```bash
.venv/bin/python -m compileall -q src tests
.venv/bin/python -m pytest -q
.venv/bin/python -m symmetrylab.cli evaluate --suite benchmarks/manifest.json --output data/evaluation-run
```

The verifier baseline achieved 30/30 correct labels on 10 Golden and 20 constructively generated Development cases. All 27 valid mathematical cases passed certificate verification. See [Implementation status](docs/implementation_status.md) for test counts and limitations. These results do not establish held-out generalization or an improvement from LLM self-improvement; experiments A/B/C/D have not been run.

## Project structure

The repository follows the Newspaper project's src layout and module boundaries:

```text
config/                    Configuration without credentials
data/                      Local run records; ignored by Git
docs/                      Mathematics, architecture, experiments, privacy, and plan
prompts/                   Reviewable prompt specifications
src/symmetrylab/
  agent_core/              Research state machine, budgets, and assembly
  model/                   Replaceable model adapter
  verifier/                Group relations, common gauge solver, and certificates
  memory/                  Counterexample-backed lessons
  communication/           Audience templates and evidence auditing
  observability/           Local JSONL traces
  evaluation/              Benchmark runner with separate labels
  tools/                   Registered data-only research operations
  database/                Local run persistence and history
  web/                     Loopback HTTP server and English interface
  mcp/                     Reserved extension boundary
benchmarks/                Golden, Development, and Held-out (currently empty)
tests/unit/                Mathematics, inputs, certificates, metamorphic checks
tests/integration/         Full loop, replay, budgets, and mocked models
```

Developers should start with [AGENTS.md](AGENTS.md). The [implementation plan](docs/implementation_plan.md), [architecture](docs/architecture.md), [experiment protocol](docs/experiments.md), and [privacy rules](docs/privacy.md) describe the intended scope and roadmap.

All public cases are newly constructed abstract toys. Private papers, SSG databases, and Mathematica research code have not been connected. Project-authored documentation, prompts, CLI text, and newly generated reports use English.
