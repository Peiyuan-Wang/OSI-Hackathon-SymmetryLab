# Paper survey and researcher voice profile

Open **http://127.0.0.1:8787/papers**. Enter interest keywords and your own papers (arXiv ID, DOI or exact title), then **Find papers**. Vote ▲/▼ to re-rank instantly; **Build from my papers & likes** creates the voice profile; tick **Use in live model runs** and, on the theory/experiment page, **Write in my research voice**.

Paper survey uses a warm plum palette, with purple navigation, controls, scores and focus indicators. Theory retains its green palette and experimental research its blue palette. The layout and paper-ranking behavior are unchanged. Desktop builds must be rebuilt to include the new stylesheet.

## Retrieval

Source: arXiv API only (`export.arxiv.org`), restricted by default to `cond-mat*`, `quant-ph`, `physics*`, `hep-th`, `math-ph`. One query per keyword plus up to four distinctive phrases from your own abstracts; 25 results each, requests spaced 3 s apart. Your papers are resolved by arXiv ID, Crossref DOI (arXiv DOIs go to arXiv), or exact-title match (Jaccard ≥ 0.6, otherwise reported as unresolved). At most 200 candidates are kept; voted papers are never dropped.

## Semantic space

**PhysBERT** (`thellert/physbert_cased`, revision `2d8340bd`, BERT pretrained on arXiv physics full texts, mean pooling, 768-d) when prepared locally; otherwise a deterministic physics-concept lexicon encoder (offline, 1024-d hashed features with ~20 synonym groups such as TMR / MTJ, Néel vector / staggered magnetization). Install with `pip install -e .[physics]` and click **Prepare PhysBERT** (~440 MB, explicit download, never implicit). Keywords are embedded as "We study ⟨keyword⟩." because short phrases pool poorly. Vectors are cached per encoder version and never mixed.

Measured on condensed-matter abstracts: unrelated fields 0.1–0.2, same subfield 0.45–0.65 (PhysBERT). Thresholds per encoder: merge 0.75 / match 0.35 / score floor 0.30 (PhysBERT), 0.50 / 0.08 / 0.05 (lexicon). These are engineering values, not validated optima.

## Ranking, feedback and drift (from Newspaper)

Ported from Newspaper's `anchored-multi-interest-v1` (`semantic_profile.py`, [newspaper_agent](https://github.com/Peiyuan-Wang/newspaper_agent)):

- Seeds = keywords (priority 2) and own papers (priority 3), merged by complete linkage into anchors.
- Q = anchor, K = V = paper vector. Attention = softmax(cos(a, x)/0.12) over anchors within 0.12 of the best and above the match threshold assigns each vote.
- Rebuilt from the current votes each time: p = unit(a + 0.75 P − 0.35 N), prior 3, 90-day half-life, clamped to 25° around the anchor; bounded affinity bias. Undo is exact.
- Score = clip((cos(p,x) + bias − floor)/span × 100), ±4 for the paper's own vote; papers no anchor explains get half score.

Added here: **interest drift**. Likes that no anchor explains are not forced into an anchor; they are clustered into *emerging interests* (with distinctive terms) and can be adopted as keywords. The panel shows the share of likes outside anchors and each anchor's shift angle. No encoder or Wq/Wk/Wv is trained.

## Voice profile

Deterministic, no model call: research focus (keywords + emerging interests), distinctive terminology (frequent in your papers ×2 and liked papers ×1, rare in the candidate pool), abbreviations as you define them, register statistics (sentence length, "we", direct claims, hedging, passive, inline math) and up to 3 + 2 exemplar sentences labelled by paper ID. Capped at 3,500 characters with a hash.

In live runs it is sent as a **second, separate system message** after the main prompt. It states that it governs wording only and never overrides tools, the JSON format, evidence labels, verification or safety, and must not be cited as evidence. Reports record the profile hash. Offline walkthroughs record it as selected but not applied.

## Storage and privacy

`data/literature/profile.json` and `vectors.json` (ignored by Git). **Clear survey & memory** deletes both. Only keywords, titles, IDs and DOIs leave the machine (arXiv/Crossref); abstracts are embedded locally.

## Limits

No full-text reading, author disambiguation, citation graph or Semantic Scholar/INSPIRE sources yet. Ranking quality on real users has not been measured; the drift indicator is descriptive, not a validated change-point test.
