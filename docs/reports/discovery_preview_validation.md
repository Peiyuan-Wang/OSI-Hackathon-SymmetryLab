# SymmetryLab v0.3 preview — acceptance record

Date: 2026-10-22 (Asia/Shanghai). Local working tree; no commit, push or release was made.

## Delivered workflow

The theory page retains the original layout. It accepts selected paper text/DOIs, interest keywords and preference corrections; the controller can propose evidence-linked research directions, collect a separate human preference and recall checked counterexamples. The experimental page uses the same layout in blue and starts with L10 MnPt and the Neel-axis measurement goal.

Sources, conditional exact calculations, model interpretations and proposed experiments have distinct statuses. The new kernels calculate director symmetry constraints and collinear neutron orientation factors using rational arithmetic. Unknown scales, sign reversal and specified domain mixtures can expose non-identifiability. These are conditional calculations, not a validated magnetic structure or experiment for the user's sample.

## Validation evidence

| Check | Outcome |
|---|---|
| Regression suite | 87 passed |
| Python compilation | Passed |
| JavaScript syntax | Passed |
| Git whitespace check | Passed |
| Public deterministic seed benchmark | 12/12; zero model calls |
| Browser experimental demo | Completed; 3 checked calculations; 1 conditional design |
| Browser theory demo | Completed; 2 proposals; keyword-linked provisional taste and preference form |
| Repository-visible credential scan | No supplied-key matches |
| Live retrieval | Crossref returned 5 metadata records; COD unavailable |
| Full live acceptance | Not passed: connection failure after a verified calculation, before experiment design |

The public seed benchmark does not measure scientific novelty, personal taste or improvement. Offline decisions are scripted. No expert preference labels or statistical RSI gains have been collected.

## Current browser records

- Experimental offline run: `c0dccd056cb74acd91c91a89721d55c1`.
- Theory offline run: `f98066ade3fd4155a534c91ffe36bb3e`.
- Latest live run: `73d8f667149b466ba8221343ebdb5c67`.

Runtime evidence is stored under `data/workbench/<run_id>/` and ignored by Git. The live run retained 7 model requests, 5 tool calls, 20,572 provider-reported tokens, 266.92 seconds, 9 source records (4 curated plus 5 retrieved), 1 structure assessment and 1 checked calculation. One speculative concatenated action was discarded. The seventh request failed with a sanitized connection/timeout error. There is no completed live design or synthesis. Failed/interrupted attempts remain in history.

## Repairs completed during final verification

- Distinguish invalid query syntax from source unavailability; formula searches require an elemental formula such as MnPt.
- Display source failures and structure assumptions in the evidence notebook.
- Retain source references and structure conditions in exported reports.
- Accept human preferences only for completed dossiers; scope keyword-only recall by keywords.
- Ignore local diagnostic output; preserve secrets in the backend environment.

## Remaining work

1. Stabilize the configured provider's multi-turn transport and obtain a complete live acceptance run; automatic checkpoint continuation is not implemented.
2. Resolve structural retrieval and validate a sample-specific chemical/magnetic model before selecting actual reflections.
3. Supply sample form, substrate/strain, temperature, growth constraints and instruments before claiming experimental feasibility.
4. Supply the researcher's selected papers; PDF/full-text extraction, a trained taste model and calibrated ranking are not implemented.
5. Collect the proposed 48-packet benchmark with blind expert judgments and run matched-budget ablations. The 12 executable seeds are only a correctness foundation.
6. Add energy stability and further measurement kernels with independent checks. No XMLD spectrum, growth recipe, absolute signal prediction or RLVR/GRPO training is delivered by this preview.

See `docs/design/discovery_benchmark_rsi.md` for the full scientific contracts, benchmark protocol and future improvement route.
