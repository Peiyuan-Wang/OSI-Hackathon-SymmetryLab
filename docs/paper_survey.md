# Paper survey and personalized research

Open **Paper survey** in the desktop app. Add keywords and your published papers, then save the profile and find papers. The page uses a plum palette; Connection uses copper, Theory green, and Experiment blue.

## Interests: history, current intent, and evidence

Expand **Research questions, methods and current intent** to enter the problems, methods, current project goal and research taste you want the agent to consider. Historical paper mentions are displayed separately by symmetry, method, observable and system, with original excerpts. These are deterministic lexicon matches, not a complete scientific parser or confirmed preferences.

Keywords have seed priority 2, papers 3, and explicit problem/method/current-goal fields 4. These engineering weights are not calibrated. Complete-linkage clustering forms multiple interest anchors. Reversible feedback moves each vector using a Rocchio-like update, a prior of 3, a 90-day half-life and a 25-degree movement cap. A single unexplained like is labelled a tentative signal, not an established interest change.

Check **Use these preferences and paper-derived topic excerpts in research planning** to supply a bounded, versioned interest packet to research runs, independently of writing personalization. It includes explicit preferences, keywords, selected historical excerpts and up to eight liked-paper titles. Current run instructions take precedence. The agent may cite this packet through `learn_taste(origin="interest_profile", ...)`, but preferences never determine mathematical truth. Sharing is off by default.

## Retrieval and ranking

Candidate retrieval defaults to arXiv, with optional Valency Bond MCP or combined search. Own-paper resolution still uses arXiv and Crossref regardless of the candidate-source selection. Physics categories are selected by default. Each search performs at most six queries per selected provider with at most 25 accepted results per query; arXiv requests are spaced three seconds apart. Query slots first cover up to two rotating keywords, a paper-derived phrase, a current-intent phrase and a positive-feedback phrase; spare slots are filled from remaining queries. This prevents six keywords from excluding all own-paper queries. Repeated searches rotate keyword coverage. Search can transmit phrases derived from current intent or liked papers.

### Optional Valency Bond MCP

1. Sign in to [Valency Settings](https://app.valency.io/settings) and copy your bearer token. Follow the official [Direct API guide](https://docs.valency.io/guides/api/).
2. Open **Paper survey → Literature sources · Valency Bond MCP**. Choose **arXiv + Valency Bond** (or Bond alone), paste the token, and select **Test Bond connection**. This applies the settings and calls `list_sources`; initialization alone is not a successful connection test.
3. Select **Find papers**. Cards show the original source where supplied and the retrieval channel(s). Search failures remain visible above the results; one provider's failure preserves results from the other.

The token stays in server memory for the current app session and is never returned to the UI, written to the survey, or embedded in a package. Restarting the app requires entering it again. Developers can alternatively set `SYMMETRYLAB_BOND_TOKEN` in the app's process environment. **Forget session token** clears only the in-memory override, not an environment variable; the UI reports which source is active. **Clear survey & memory** also clears the session token. Source choices persist, so a restarted app with Bond selected will report a missing token until configured again.

The fixed endpoint is `https://mcp.valency.io/`. The standard-library client performs MCP initialization, negotiates a supported protocol version, sends `notifications/initialized`, carries session/protocol headers, and handles JSON or streamed JSON-RPC responses. It rejects redirects and bounds response sizes. It discovers tool schemas with `tools/list` and invokes `semantic_search_papers`; unknown required parameters and unsupported output formats produce visible errors. No tools other than `list_sources` and `semantic_search_papers` are called. No SDK, Node runtime, browser login automation, or new package dependency is required.

Bond results enter the existing local embeddings, ranking, feedback and writing-selection pipeline. Deduplication uses canonical arXiv IDs and DOIs, never title similarity, and retains existing paper IDs and votes. Records without shared identifiers may remain duplicated. With **Physics categories only** enabled, Bond records must have recognizable physics category metadata; unclassified journal records are omitted. Uncheck the option to include them. Counts are accepted results before deduplication, not the provider's total corpus matches. Changing source selection affects future queries and does not remove previously saved papers.

Scope: this integration adds a source to **Paper survey**. It does not add Bond to the Theory/Experiment agent's separate `search_source` tool, implement OAuth login/token refresh, fetch full texts, or automatically verify scientific claims. Sharing survey interests with research runs remains a separate opt-in.

Validation uses synthetic MCP responses and local HTTP API tests. The unauthenticated endpoint was reachable and rejected a request without an Authorization header. Authenticated `list_sources`, actual search schemas/results, coverage beyond arXiv, and account quota behavior still require a user token and live validation. The adapter deliberately reports incompatible schemas instead of assuming that an empty result means the query succeeded. This feature is included in v0.3.2 source and desktop packages; the previously published v0.3.1 binaries do not contain it.

The candidate pool aims for 200 entries. Content-voted and writing-selected papers are retained even if protected entries exceed that cap. Title and abstract text is clipped to 2,000 characters for embeddings.

PhysBERT is used only when dependencies and pinned weights are prepared locally; lite desktop packages use the deterministic 1,024-dimensional physics lexicon. Downloads are explicit. Vectors are cached per encoder version. No encoder or attention matrices are trained.

Ranking now combines 85% anchored semantic score and 15% corpus-normalized BM25, with a +4/-4 explicit content-vote adjustment. Components are visible on cards. This is a transparent, uncalibrated baseline, not a probability or established improvement over the old ranker. Historical feedback does not independently prove novelty or scientific usefulness.

## Separate content and writing feedback

**Like / Not for me** updates research relevance. **Use writing style** selects a paper as a writing source without changing content votes or ranking. Own-paper abstracts and explicitly selected writing sources supply candidate terminology and examples. Corpus phrases are not treated as authoritative field terminology.

Set the target reader, section (abstract, derivation, discussion, experiment or limitations), explanation depth and writing preferences. Optionally add up to eight approved paragraphs, each labelled by section. Paragraphs must contain 20–1,500 characters. Save preferences, then choose **Build from approved sources**. Keywords alone cannot build a writing voice.

The deterministic profile includes observed register statistics, terminology candidates, abbreviations and bounded examples. Whole lines are included within the 3,500-character budget. A corpus fingerprint marks the profile stale after own-paper, writing-selection, keyword, paragraph or writing-preference changes. Content votes and unrelated search results do not change the writing fingerprint. Stale profiles must be rebuilt before use; old profiles from previous versions require one rebuild.

## Dedicated writing pass

Enable **Use in live model runs**, then select **Write in my research voice** in the research workspace. The writing profile is no longer inserted into every planning call. Once the agent produces a final synthesis, a separate editor call receives:

- the original synthesis and limitations;
- an immutable ledger of checked calculation results;
- the bounded writing profile and selected audience/section/depth;
- at most two approved paragraphs, prioritizing section match and then task overlap.

The editor receives no tools. It must return a summary and every ledger ID. Structural validation rejects malformed output, changed ledger references and numeric tokens absent from the original synthesis or evidence. These checks do **not** prove semantic faithfulness: negations, causal relationships, omitted conditions and evidence overstatement still need expert evaluation. The rendered report retains checked facts separately and labels generated prose as unverified.

The call consumes the existing model/token/time budgets. Failure, cancellation, invalid output or insufficient budget retains the original synthesis. Successful runs save `original_model_summary`, `writing_audit` and the profile hash; scientific evidence is never rewritten. Offline demonstrations retain fixed wording and do not claim to apply a live writing model. The main synthesis uses the selected writing audience; report audience tabs still add deterministic supporting sections rather than independently rewriting the synthesis for each tab.

## Storage and privacy

Profiles, feedback, samples and vector caches live in the local literature data directory, excluded from Git. Embeddings are computed locally. Search queries go to the selected arXiv/Bond providers; own-paper identifiers and titles go to arXiv/Crossref. When enabled, interest packets and selected writing context go to the configured model API and are represented in local run records. Review the selection before including unpublished work. **Clear survey & memory** removes the local literature store.

## Validation and remaining work

Regression tests cover query-source coverage, feedback separation, stale-profile rejection, paragraph selection, planning-context propagation and editor rejection/fallback. They use synthetic fixtures and model doubles. No claim of improved real-user ranking or writing quality follows from passing these tests.

Full-text parsing, author/contributor disambiguation, a curated field-convention registry, trained preference models, SPECTER2 integration, diversity-aware reranking and held-out expert quality evaluation remain future work. See [the LaMP research review](reports/lamp_personalization.md) for methods and an evaluation plan.
