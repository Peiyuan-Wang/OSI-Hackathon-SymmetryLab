# Experiment Protocol and Observed Results

Only the deterministic verifier has been evaluated so far: experiment arm E in the plan. The 10 Golden cases use hand-derived labels from the plan. The 20 Development cases are constructed using q=(R-I)theta and are all valid trivial cases. They do not estimate broad generalization to nontrivial classes. No held-out results are available.

Expected labels are separated from inputs in the manifest. The demo reads Golden inputs and never sends the expected field to the model. Evaluation records each expected and actual status, certificate verification, and input hash. Invalid group actions are excluded from valid gauge-classification statistics.

See implementation_status for observed results and data/evaluation-v0.1 for the complete local records. Real-API ablations A (single-shot LLM), B (equal-budget retries), C (verifier feedback), and D (feedback plus memory) have not been run. No improvement over retries is claimed.

Future comparisons must freeze group-family splits, model versions, budgets, and questions. Basis changes or alternative integer representatives of Golden cases must not leak into held-out data. Report classification accuracy, unknown coverage, counterexample detection, certificate validity, revision success, unsupported proof claims, model requests, and actual token costs separately. Do not change the denominator of failed tasks after observing results.
