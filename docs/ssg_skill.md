# SSG skill integration

The application exposes `list_skills`, `read_skill`, and `call_skill` through the existing bounded model-action loop. Both theory and experiment tracks can use the SSG skill. The fixed Verification scope block has been removed from the interface; individual results retain their mathematical conditions and provenance.

## Installed assets

The authorized SQLite 0.1.5 catalog and Wolfram paclet 0.12.1 are copied unchanged into `data/ssg/`. `manifest.json` contains SHA-256 hashes and sizes. The catalog contains 67,475 stored SSG labels. Original manuscripts were not copied. Local scientific assets remain excluded from Git by the existing data rules; publishing them requires a separate distribution decision.

The runtime uses the original SQLite schema 3, with read-only connections and parameterized queries. It does not convert or flatten the scientific data into a new invented schema. A source checkout automatically finds `data/ssg/SSGReciprocalOffline-0.1.5.sqlite`. Set `SYMMETRYLAB_SSG_CATALOG` to select another authorized local copy. Restart the application after changing this environment variable.

The paclet is preserved for future Wolfram-backed recomputation. The current integration does not execute it or claim to implement all its functions. Its original guide is copied to `data/ssg/UserGuide.md`.

## Model workflow

1. Discover and read `ssg-database`.
2. Inspect metadata; search by Xiao label, parent space group, magnetic order, BNS identifier or nonsymmorphic flag.
3. Fetch summary, reciprocal/O(3) data, MG/family-group correspondence or paginated generators/elements.
4. Call `momentum_orbit` or `verify_group` when relevant.
5. Cite source IDs and SSG calculation IDs in proposals. The source ledger and report preserve the results.

Example tool action:

```json
{"action":"tool","name":"call_skill","arguments":{"skill":"ssg-database","operation":"momentum_orbit","arguments":{"record_id":"N143.10.1","k":["1/3",0,"1/2"]}},"reason":"Compute the reciprocal orbit from the stored graded action."}
```

The exact contract and mathematical cautions are maintained in [SKILL.md](../src/symmetrylab/skills/ssg-database/SKILL.md).

## Computation and evidence

Momentum orbits use rational arithmetic. Group verification compares generator closure with the stored finite graded reciprocal group, including identity, duplicate checks, unimodularity and declared order. Generation of the entire stored set with closure under right multiplication by invertible generators establishes its group closure. Calculations obey the controller deadline and use no model-authored executable code.

The antiunitary sign is already included in the stored reciprocal matrix. BNS correspondences describe reciprocal MGs, not real-space material assignments. Catalog coverage applies to stored parameter choices. The integration does not certify every continuous specialization, recompute the full O(3) classification, solve new Hamiltonians, or infer material symmetry from a chemical formula.

## Packaging

The desktop builds (`scripts/build_mac_app.sh`, `scripts/build_windows_app.ps1`) bundle the SQLite catalog by default after checking its SHA-256 against `data/ssg/manifest.json`; a missing or altered file stops the build. `--no-ssg` / `-NoSsg` (or `SYMMETRYLAB_BUNDLE_SSG=0`) builds without it. The built app is smoke-tested with `--require-ssg`: record count 67,475 and `verify_group` on N143.10.1 must pass inside the frozen app. The paclet is not bundled (not needed by the Python runtime). The catalog is never committed to Git; share an app that contains it only where its licence allows.

## Offline walkthrough

A theory question that mentions SSG / spin space groups runs a scripted walkthrough: read the skill, metadata, search parent group 143, fetch N143.10.1, `verify_group` (order 6), orbit of k = (1/3,1/5,1/7) (size 6) and of K = (1/3,1/3,0) (size 2, stabilized by the unitary threefold rotations), then one proposed direction. All numbers come from the catalog; the script only chooses the order of calls.
