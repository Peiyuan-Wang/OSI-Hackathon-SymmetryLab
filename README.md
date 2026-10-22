# SymmetryLab

**A verifiable research agent for condensed matter symmetry questions**

*Roadmap goal: measurable self-improvement. Current status: rechecked lessons from earlier runs change later plans (shown in the workbench); no learning gain has been measured yet.*

SymmetryLab supports two research workflows: experimental goals for a named material, and theory exploration guided by selected papers and interests. Exact tools check bounded models; source-linked interpretations, research taste, material assignments and experimental proposals retain their own verification status.

The **v0.3 preview** preserves the original theory layout and adds a matching experimental workspace for **L10 MnPt Neel-axis detection**. It includes public metadata retrieval, conditional orientation calculations, counterexample search, paper-linked taste profiles, human preference feedback and rechecked cross-run strategies. Live model research requires a configured provider. Offline walkthroughs use scripted decisions.

Read [the discovery benchmark and RSI design](docs/design/discovery_benchmark_rsi.md) for scientific definitions, source boundaries, the benchmark collection plan, controlled experiments and remaining work. This is a research prototype; sample-specific magnetic structure, growth feasibility, quantitative experimental signals and novel discoveries are not established.

## Desktop app (macOS)

```bash
scripts/build_mac_app.sh && open dist/SymmetryLab.app
```

Installs all dependencies into `.venv`, runs the tests and builds a native app with the same layout. Add `--lite` to leave out PyTorch/PhysBERT. Details: [Desktop app](docs/desktop_app.md).

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

Open **http://127.0.0.1:8787/** for theory or **http://127.0.0.1:8787/experiment** for experimental research. Select **Offline demonstration**, then **Start research** to try the complete loop without a key. This mode uses a scripted policy and real exact mathematics; it is explicitly labeled throughout the interface.

What the two offline walkthroughs show:

- **Theory:** the claim "every nonzero shift is gauge-nontrivial" is refuted by an exact counterexample (inversion with a half shift, θ = (3/4, 0)), contrasted with a certified obstruction (half-period translation), then two follow-up directions are proposed.
- **Experiment (L10 MnPt):** assuming C4z domain symmetry allows only the c axis, assuming C2z allows every listed axis — so symmetry alone does not decide the Néel axis. A c-only neutron probe leaves basal-plane axes tied; four nonparallel probes separate them except for the n / −n sign. A conditional diffraction design follows.
- **Run it twice:** the second run recalls the rechecked lesson from the first; the theory run no longer re-proposes the refuted claim and the experiment run skips the degenerate c-only probe (one fewer tool call). This is a scripted demonstration of the memory mechanism, not a measured improvement.

The workbench displays the plan, each tool call with its purpose, exact certificates and recalled lessons. Every report starts with **Key findings** derived from checked records. Switch the audience (Researcher: full tables and controls; Physics student: concepts explained; General reader: short summary) or download Markdown and evidence JSON. Completed runs remain in local history. **Stop run** requests cooperative cancellation; an in-flight model request may take up to its network timeout to return. Keep the terminal running; Ctrl+C stops the server.

### Paper survey

Open **http://127.0.0.1:8787/papers** to rank arXiv papers against your keywords and own papers, re-rank by likes, see interest drift, and build a *researcher voice profile* that live runs can use as a style-only system prompt. Optional PhysBERT encoder: `.venv/bin/python -m pip install -e ".[physics]"`, then **Prepare PhysBERT** on the page. See [Paper survey](docs/paper_survey.md).

### Choose a research workflow

- **Experimental research:** enter the material, observational goal, sample conditions and instruments. The default MnPt walkthrough compares candidate axes, exposes ambiguous geometries and produces a conditional neutron-measurement plan. Its normalized factors are not absolute intensities or verified accessible reflections.
- **Theory exploration:** enter an interest direction, keywords and selected paper titles/DOIs/excerpts. A text or Markdown reading list can be imported locally. Live mode can infer preferences with source excerpts and retrieve DOI metadata. After a run, compare the first two proposed directions and explain your choice; later runs with the same selected-paper context can use that feedback.
- **Offline demonstration:** fixed walkthroughs exercise actual exact tools without a model or network. **Live model research** performs question-dependent planning and bounded public retrieval.

Use only paper text you intend to share with the chosen provider. The application never scans paper folders automatically. Model-generated prose remains unverified even when it cites a checked calculation.

### Connect a model

Open **Connection** in the sidebar. Enter the service's Base URL (ending at `/v1`, without `/chat/completions` or `/responses`), the model ID, the protocol (**Chat Completions** or **Responses**) and your API key, click **Test connection**, then **Save**. Settings are stored on this computer in `connection.json` (user-only permission 0600, not encrypted); the key is never shown again or written to run records. Any OpenAI-compatible service works. If no key is saved, `SYMMETRYLAB_API_KEY` from the environment is used.

**Validation boundary:** adapters and adaptive behavior are covered by tests with model doubles. The new workflow has not yet been validated against a real model provider. See the dated implementation status for source-service and browser checks.

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

# Edit base_url/model in a copy of config/live.example.json and export SYMMETRYLAB_API_KEY first
.venv/bin/python -m symmetrylab research --mode live --config config/live.example.json --goal "Explore valid C2 actions and find a gauge counterexample" --output data/research-live
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

Repository layout:

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
  mcp/                     Placeholder for a future MCP integration (empty)
benchmarks/                Golden, Development, and Held-out (currently empty)
tests/unit/                Mathematics, inputs, certificates, metamorphic checks
tests/integration/         Full loop, replay, budgets, and mocked models
```

Developers should start with [AGENTS.md](AGENTS.md). The [implementation plan](docs/implementation_plan.md), [architecture](docs/architecture.md), [experiment protocol](docs/experiments.md), and [privacy rules](docs/privacy.md) describe the intended scope and roadmap.

All public cases are newly constructed abstract toys. Private papers, SSG databases, and Mathematica research code have not been connected. Project-authored documentation, prompts, CLI text, and newly generated reports use English.
