# Discovery benchmark, research taste and scoped improvement

Status: v0.3 preview, 2026-10-22. This design separates implemented mechanisms from proposed experiments. No autonomous discovery advantage, expert-taste accuracy or weight-training result has been measured.

## 1. Two different research contracts

**Experimental research** starts with a material and an observational goal. The first case is L10 MnPt: distinguish competing Neel-axis orientations. The output must identify the sample conditions, source-supported structural possibilities, conditional hypotheses, computed consequences, ambiguous alternatives, a feasible-measurement checklist and a falsifier. The hypothesis must relate to the requested observable. A correct toy calculation alone cannot finish the material task.

**Theory exploration** starts with papers, interests and constraints, without a mandatory experimental objective. Outputs are alternative research directions with a mechanism, a minimal represented object, a bounded first test, a counterexample strategy and an explicit reason for personal relevance. An interesting negative result can be valuable. A preference score must never override a failed mathematical check.

The UI retains the existing sidebar, research composer, activity stream, evidence notebook and report. Theory uses `/`; experimental research uses `/experiment` and a blue palette.

## 2. L10 MnPt: what the first dossier can establish

Keep four records separate:

1. Chemical structure and sample phase. Published L10 MnPt models use P4/mmm (123). Chemical symmetry alone does not assign an ordered magnetic state.
2. Magnetic structure: propagation vector, site basis, ordering, domains, coordinate convention and MSG/SSG. An unverified model-generated label is not an assignment.
3. Sample conditions: bulk or film, substrate, thickness, temperature, strain, stoichiometry and chemical order. Do not transfer a bulk easy-axis result to an unspecified film.
4. Measurement model: instrument, reciprocal basis, magnetic structure factors, geometry, background and uncertainty.

The reference packet contains public studies with different assumptions. A bulk equiatomic calculation supports c-axis moments; MnPt/BaTiO3 and strain studies predict condition-dependent alternatives. These references motivate competing hypotheses, not a unique answer for a new sample. See the primary references below.

### Implemented exact kernels

For a collinear magnetic structure, the normalized unpolarized neutron orientation factor is

`P(n,Q) = 1 - (n·Q)^2 / [(n·n)(Q·Q)]`.

Inputs are nonzero rational Cartesian vectors. This is the orientation factor after separating the magnetic structure factor, not an absolute scattering intensity. Nonzero magnetic reflections and the required normalization must be established independently. Miller indices must be converted using the sample reciprocal basis; integer Cartesian vectors in a demo are not assigned accessible reflections.

The verifier computes exact fractions, and a separate checker uses the cross-product identity `|n × Q|²/(|n|²|Q|²)`. It enumerates exactly identical response rows and rows proportional under an unknown common positive scale. It also evaluates specified incoherent domain mixtures with nonnegative populations summing to one. Finite candidates do not establish identifiability over every possible direction or domain distribution. Unknown separate scale factors per reflection invalidate the assumed comparison.

A second kernel tests `R D R^T = D`, where `D = n n^T / |n|²`, for supplied rational orthogonal Cartesian operations of an assumed single magnetic domain. An independent check tests `Rn = ±n`. This is a necessary director constraint. It does not determine sublattice permutations, translational phases or physical MSG realization. Applying the whole chemical parent point group to a symmetry-broken ordered domain can incorrectly exclude an axis; the demo explicitly labels the C4 premise as hypothetical.

### First experiment design

Compare c-axis, in-plane axial and diagonal hypotheses plus sign reversal and mixed domains. A single Q parallel to c cannot distinguish in-plane axes. Additional nonparallel directions can separate some candidates, but the unpolarized factor remains even under `n → -n`.

The conditional protocol requires chemical and magnetic refinement, accessible nonzero magnetic reflections, corrected relative intensities, competing-domain fits and uncertainty analysis. For films with inadequate neutron signal, XMLD is a possible alternative requiring a spectral model, structural-dichroism controls and instrument assessment. XMLD, AMR, DFT energies and full neutron structure factors are **not calculated** by this preview. There is no validated growth recipe or numerical signal-size prediction.

## 3. Source retrieval and provenance

Implemented sources:

- COD public JSON metadata search by Hill formula or text. Keep up to five matches; retain record IDs, chemical space-group fields, cell parameters when present, retrieval timestamp and response hash. Multiple matches remain alternatives. No CIF/mCIF parser or automated magnetic refinement is implemented.
- Crossref DOI or bibliographic search. Use titles and available abstracts as search leads. Do not imply full-text coverage or infer physical truth from ranking.
- Curated MnPt primary-source context, clearly distinguished from a live retrieval.

On 2026-10-22, Crossref live search returned five MnPt-related records. The documented COD endpoint returned non-JSON content in this environment; the explicit PHP entry also failed during the connectivity check. No live COD structure result has been validated. The MnPt source packet remains curated literature context.

Searches are bounded to six per run and 25 unique source records. Endpoint URLs are constructed from fixed public services; the model cannot request arbitrary URLs, access local services through retrieval or execute source text. Failures return `unavailable`, not absence of a physical effect. Retrieval results and model interpretations remain separate records.

Future priority: an authorized magnetic-structure source adapter, versioned mCIF ingestion, symmetry-operator conversion, magnetic propagation-vector handling, source claim extraction with page/section evidence, and explicit conflict resolution. MAGNDATA bulk downloads have access conditions; do not quietly scrape around those conditions.

## 4. Learning personal research taste

A skill or system prompt is a policy description, not trained weights. The preview uses a context-derived preference model:

- The researcher selects titles, DOIs, abstracts or relevant excerpts from their own papers and enters interest keywords. No automatic scan of private paper folders occurs.
- The live policy retrieves DOI metadata when needed and proposes preferences with exact supporting excerpts and source IDs. Each inference is marked pending researcher confirmation.
- Distinguish problem choice, explanatory style, mathematical tools, evidence standard, tractability, and desired research risk. A coauthored paper does not reveal which contribution the researcher prefers; accept explicit contribution notes.
- The researcher can correct the profile and compare two generated directions, choosing either, a tie, or neither, with a reason. These labels are stored separately from immutable run results.
- Later runs with the same supplied paper context receive those human judgments. A changed paper context does not silently inherit the previous preference. Current explicit corrections take precedence.

Implemented: source-linked preference inference, paper-text import, corrections, pairwise UI feedback and scoped recall. Not implemented: PDF understanding, automatic author disambiguation, statistical preference fitting, calibrated ranking, DPO or fine-tuning. The UI currently compares the first two proposals; a broader randomized comparison interface is future work.

Do not use venue prestige, citation counts, model confidence or publication status as personal-taste labels. Preserve rejected directions and reasons: “wrong”, “already known”, “not my interest”, “too expensive”, and “interesting but premature” are different outcomes.

## 5. Benchmark structure

Use three separately reported layers.

| Layer | Task and evidence | Evaluation |
|---|---|---|
| Reliability | Exact instances, source/phase ambiguity, invalid inputs, unsupported tasks, fabricated references and counterexamples | Executable checks, independently checked certificates, correct abstention, source entailment review |
| Direction quality | Blind comparison of proposals under a fixed personal profile and resource budget | Researcher/expert preferences, mechanistic depth, testability, tractability, diversity, novelty relative to a fixed source corpus |
| Research utility | Spend a bounded follow-up budget on selected directions | Valid results, useful negative results, time to decisive evidence, changed decisions, expert editing effort |

Do not collapse all three into one leaderboard number. A certificate is a correctness gate for that computation, not an interestingness score. A preference is a human judgment, not a scientific theorem.

### Implemented public seed suite

`benchmarks/discovery/seed.json` contains 12 cases: axis-versus-plane factors, sign degeneracy, incomplete geometry, unknown scale, zero signal, domain ambiguity, an added discriminating direction, rational geometry, invalid zero/float/population input, and a nonorthogonal supplied operation. All are public seed cases, not held-out evidence. Run:

```bash
.venv/bin/python -m symmetrylab.evaluation.discovery --output data/discovery-evaluation-001
```

The legacy 30-case affine suite remains separate. Neither evaluates material novelty or scientific taste. The preference packet under `benchmarks/discovery/` is an unlabelled annotation template, not fabricated expert data.

### Proposed first research dataset

Create 48 packets before model comparisons:

- 12 reliability packets around magnetic orientation, nuisance parameters, source conflicts and unsupported physics.
- 12 retrospective theory packets: freeze public knowledge before a result appeared, mask later papers, ask for a plausible first test; evaluate against known results without requiring verbatim rediscovery.
- 12 researcher-profile packets, each with two to four selected papers, contribution notes, interests, negative preferences and a resource budget. Generate competing proposals under blinded order.
- 12 prospective open-direction packets: no known final answer; score bounded research progress and calibrated uncertainty.

Use 24 development, 12 validation and 12 sealed test packets, split by mechanism family, paper cluster and material family. Do not random-split paraphrases or nearly identical matrices. Time-cutoff corpora need timestamped snapshots. Hold out some researchers if claiming transfer to new personal tastes. Maintain provenance and de-duplication hashes. The 48 packets are a collection plan and have not been created or labelled.

Two knowledgeable reviewers should independently annotate source entailment, unsupported physical inference and obvious prior art. The target researcher supplies personal preference labels. Preserve disagreements and abstentions rather than presenting a majority as objective taste. Randomize proposal order, hide policy identity, and disclose conflicts.

Metrics: exact validity, false certification, unsupported source assertions, correct abstention, counterexample detection, preference agreement with uncertainty, expert pairwise ranking, accepted directions per budget, diversity by mechanism, and cost/time to a decisive test. Report paired confidence intervals and individual-profile results; a small seed suite cannot support population claims.

## 6. Controlled experiments

Freeze the model/provider, prompts, source snapshots, tools, verifier version and evaluation rubrics. Match model-call and token budgets and record actual usage, not just maximum limits.

- A: one-shot idea generation with the same source/profile packet.
- B: repeated generation or self-critique at the same total budget.
- C: iterative verifier feedback within the run.
- D: C plus independently rechecked cross-run lessons.
- E: D plus paper-derived profile and human preference feedback.

Ablate retrieved sources, profile evidence and human feedback separately. Use multiple random seeds; compare on paired packets. Never populate memory with held-out expected answers. An offline scripted walkthrough is an interface demonstration, not an A/B result or learning curve. Live-provider availability and costs must be logged; failed or exhausted runs stay in the denominator.

A useful presentation includes: one model-generated hypothesis, a genuine computed counterexample, the model's revision, a narrowed claim, and a source-linked report. A second presentation compares two differently profiled researchers receiving different proposed directions while the same mathematical evidence remains unchanged.

## 7. Scoped RSI loop

Discovery runs default to 24 policy turns, 24 tool calls, 400,000 conservative token-reservation units and 600 seconds; an individual in-flight model request may take up to 120 seconds, bounded by the remaining run time. Source requests have shorter separate limits. Legacy runs retain their earlier total budgets. The UI allows the model-turn budget to be reduced. A provider may return multiple concatenated action objects: only the first is applied, the rest are discarded and counted, and actual observations are returned on the next request. This is protocol recovery, not execution of a speculative action batch.

Implemented loop:

`plan → source/candidate → exact test → counterexample → revised action → dossier → human preference → later scoped recall`.

Only independently rechecked orientation or executable gauge counterexamples become reusable strategy records. Recall regenerates strategy text from code and checked evidence, not from previous free-form model claims. Each entry retains its originating run and calculation or predicate. Demo and live memories are separated. Human preferences are a separate channel and cannot override scientific validity. Feedback requires a completed dossier. Without selected-paper text, recall additionally requires identical interest keywords.

This is inference-time adaptation, not demonstrated recursive weight improvement. The model cannot modify the verifier, benchmark labels, reward function, source-access policy or its own executable tools.

Future policy-improvement loop: propose a prompt/retrieval-policy change from development failures; execute on frozen development and validation packets; accept only if reliability remains noninferior and utility improves with uncertainty under equal budgets. Store policy version, rollback target and acceptance evidence. Keep sealed test data out of selection. No automatic source-code self-modification is planned for the preview.

RLVR/GRPO can later train tool selection and scoped claims using verified outcomes. Reward source validity, correct calculations, useful counterexamples and honest abstention; penalize unsupported certification and budget violations. Use human preference modeling for taste separately, with uncertainty. A combined reward must not trade away hard correctness gates for persuasive prose. Training requires held-out families, reward-hacking tests and real trajectory data; none has been performed.

## 8. Implementation priorities and acceptance

Implemented preview acceptance: both routes preserve the original layout; all report fields distinguish source, interpretation, exact consequence and proposed experiment; unknown materials in offline mode remain incomplete; tampered calculations fail rechecking; profile excerpts must exist; feedback requires real proposal IDs and a local request token; source errors are visible; legacy CLI behavior stays compatible.

Next highest-value work:

1. Obtain the researcher's sample conditions, instruments and selected paper set.
2. Validate the configured live provider end to end and collect actual adaptive trajectories.
3. Add magnetic structure ingestion and reciprocal-basis conversion before assigning real reflections.
4. Implement a second physically justified measurement kernel, prioritizing sample-specific XMLD only with appropriate inputs and references.
5. Annotate the first blinded preference packets and run the matched-budget ablations.
6. Add energy stability/Hamiltonian tools through bounded structured inputs and independent tests.

## References and evidence boundaries

- [COD official REST API](https://wiki.crystallography.net/RESTful_API/): supported metadata queries and formula convention.
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/): bibliographic retrieval; metadata is not full-text verification.
- [MnPt excitations, PRB 107, 064412](https://schleife.matse.illinois.edu/wp-content/publications-data/pdf/PhysRevB.107.064412.pdf): chemical structure and a specified theoretical magnetic model.
- [MnPt properties, Materials Transactions 47, 2](https://www.jstage.jst.go.jp/article/matertrans/47/1/47_1_2/_article): equiatomic c-axis result and composition scope.
- [Ferroelectric control, PRB 104, 144403](https://journals.aps.org/prb/abstract/10.1103/PhysRevB.104.144403): interface/thickness-dependent theoretical anisotropy.
- [Strain control of the Neel vector](https://arxiv.org/abs/1903.00413): theoretical strain dependence.
- [ILL magnetic-structure lecture](https://workshops.ill.fr/event/306/attachments/264/1033/O08-Alfinelli.pdf): perpendicular-moment neutron-scattering projection.
- [Can LLMs Generate Novel Research Ideas?](https://arxiv.org/abs/2409.04109): motivation for separating blind novelty/feasibility judgments, self-evaluation and subsequent execution. Its NLP findings do not establish performance in condensed matter.

The benchmark and RSI design above is a project proposal informed by these boundaries; no cited source validates the proposed SymmetryLab implementation or predicts its performance.
