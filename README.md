# SymmetryLab

**A verifiable research agent for condensed matter symmetry questions**

*Roadmap goal: measurable self-improvement. Current status: rechecked lessons from earlier runs change later plans (shown in the workbench); no learning gain has been measured yet.*

SymmetryLab supports two research workflows: experimental goals for a named material, and theory exploration guided by selected papers and interests. Exact tools check bounded models; source-linked interpretations, research taste, material assignments and experimental proposals retain their own verification status.

The **v0.3.2 preview** preserves the original theory layout and adds a matching experimental workspace for **L10 MnPt Neel-axis detection**. It includes public metadata retrieval, conditional orientation calculations, counterexample search, paper-linked taste profiles, human preference feedback and rechecked cross-run strategies. Live model research requires a configured provider. Offline walkthroughs use scripted decisions.

**New in v0.3.2:** Paper survey now supports [Valency MCP Bond](https://www.valency.io/bond/) alongside arXiv, with combined retrieval, source attribution and identifier-based deduplication. See [Bond setup](#use-valency-mcp-bond). The v0.3.2 desktop packages include this integration; older v0.3.1 packages do not.

Read [the discovery benchmark and RSI design](docs/design/discovery_benchmark_rsi.md) for scientific definitions, source boundaries, the benchmark collection plan, controlled experiments and remaining work. This is a research prototype; sample-specific magnetic structure, growth feasibility, quantitative experimental signals and novel discoveries are not established.

## Desktop app (Windows and macOS)

Download the matching ZIP from the [latest GitHub Release](https://github.com/Peiyuan-Wang/OSI-Hackathon-SymmetryLab/releases/latest). On Windows, extract the whole folder and double-click `SymmetryLab.exe`; on Apple Silicon Mac, extract and open `SymmetryLab.app`. Default packages omit the optional PhysBERT runtime. See [Desktop app](docs/desktop_app.md) for requirements and full builds.

Build locally on macOS:

```bash
scripts/build_mac_app.sh && open dist/SymmetryLab.app
```

Installs all dependencies into `.venv`, runs the tests and builds a native app with the same layout, including the SSG catalog (downloaded and hash-checked against `data/ssg/manifest.json`). The finished app is smoke-tested. Add `--lite` to leave out PyTorch/PhysBERT, `--no-ssg` to leave out the catalog. Details: [Desktop app](docs/desktop_app.md).

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

### SSG catalog

Ask a question that mentions spin space groups / SSG. Offline, a scripted walkthrough searches the catalog for groups over P3 (No. 143), re-verifies N143.10.1 exactly and compares a generic momentum orbit with the K-point orbit. In live mode the model uses `list_skills` / `read_skill` / `call_skill` itself. Source checkouts read `data/ssg/SSGReciprocalOffline-0.1.5.sqlite`; the desktop app carries its own copy.

### Paper survey

Open **http://127.0.0.1:8787/papers** to rank papers from arXiv and optionally Valency Bond against your keywords and own papers, re-rank by likes, see interest drift, and build a *researcher voice profile* for the separate writing pass after live research. Optional PhysBERT encoder: `.venv/bin/python -m pip install -e ".[physics]"`, then **Prepare PhysBERT** on the page. See [Paper survey](docs/paper_survey.md).

#### Use Valency MCP Bond

Bond is an optional literature source; arXiv remains the default. The integration uses the official remote MCP server at `https://mcp.valency.io/`, with Streamable HTTP and bearer-token authentication. It requires no additional runtime dependency or model API key for paper search.

1. Sign up or sign in to [Valency](https://app.valency.io/login), then obtain a bearer token from [Valency Settings](https://app.valency.io/settings). See the official [Direct API setup guide](https://docs.valency.io/guides/api/).
2. Start the latest source with `.venv/bin/python -m symmetrylab serve` and open **Paper survey**. On Windows use `.venv\Scripts\python.exe -m symmetrylab serve`.
3. Expand **Literature sources · Valency Bond MCP**. Choose **arXiv + Valency Bond** for combined search, or **Valency Bond** to query only Bond.
4. Paste your token into **Bond bearer token**, then click **Test Bond connection**. This saves the source choice, keeps the token in memory and calls Bond's `list_sources` tool. The success message confirms an authenticated tool call, not just a reachable server.
5. Add interest keywords, for example `spin-space groups` and `altermagnetism`, then click **Find papers**. The app discovers the search-tool schema and invokes `semantic_search_papers`; returned records enter the existing ranking and feedback pipeline.

Paper cards show the original source where available and whether they were retrieved through arXiv, Bond, or both. Matching arXiv IDs and DOIs are deduplicated while existing votes are retained. Search errors are displayed without discarding results from the other provider. Papers without shared identifiers may remain duplicated; changing sources does not remove earlier results.

**Token handling:** the token stays only in the current app session and is never saved to the survey, reports or desktop package. Enter it again after restarting. Developers can alternatively supply `SYMMETRYLAB_BOND_TOKEN` in the app's process environment. **Forget session token** clears the in-memory token; an environment token remains active until removed from the environment. Never commit tokens to the repository.

**Filtering and scope:** with **Physics categories only** selected, Bond records without recognized physics category metadata are omitted; uncheck it to include those records. Search phrases go to the selected providers. Resolving your own paper IDs, DOIs and titles still uses arXiv/Crossref. This integration covers Paper survey; the Theory/Experiment agent's separate source tools do not yet call Bond. OAuth login, token refresh and full-text retrieval are not implemented.

**Validation:** the MCP adapter and local HTTP workflow pass tests using synthetic responses. Live authenticated Bond searches, actual response compatibility and coverage beyond arXiv still need validation with a user token. A successful connection test does not by itself validate search. See [implementation status](docs/implementation_status.md) and [detailed setup and limitations](docs/paper_survey.md#optional-valency-bond-mcp).

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
  literature/              Paper survey, arXiv/Bond adapters, ranking and feedback
  mcp/                     Valency Bond Streamable HTTP MCP client
benchmarks/                Golden, Development, and Held-out (currently empty)
tests/unit/                Mathematics, inputs, certificates, metamorphic checks
tests/integration/         Full loop, replay, budgets, and mocked models
```

Developers should start with [AGENTS.md](AGENTS.md). The [implementation plan](docs/implementation_plan.md), [architecture](docs/architecture.md), [experiment protocol](docs/experiments.md), and [privacy rules](docs/privacy.md) describe the intended scope and roadmap.

The [Research Workflow and Interest Algorithm](docs/algorithm_flowchart.md) diagrams
show how Theory, Experiment, and Papers produce personalized research reports,
and how attention-routed feedback adapts interests and measures drift.

The gauge benchmark cases are newly constructed abstract toys. The SSG Reciprocal Offline catalog 0.1.5 (67,475 records) is connected read-only as a model skill and bundled into the desktop app; its separate data release is pinned and verified by SHA-256, while the database file stays out of Git (see [SSG skill](docs/ssg_skill.md)). Private papers and Mathematica code are not connected, and the Wolfram paclet is not executed. Project-authored documentation, prompts, CLI text, and newly generated reports use English.
