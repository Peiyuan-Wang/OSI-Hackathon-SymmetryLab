# Material Explorer: Handoff and Validation Scope

## Run

Use Python 3.11 or later. Create a fresh virtual environment on the receiving computer; do not copy the sender's environment.

On macOS or Linux, use the existing project environment after installation:

```bash
.venv/bin/python -m symmetrylab serve
```

On Windows, install and run with PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -m symmetrylab serve
```

Open `http://127.0.0.1:8787/materials`. The original workbench remains at `/` and retains its original commands, tools, reports, and offline demonstration. A new navigation link connects the pages.

## What is implemented

- Material name, conditions, and separate SG / MSG / SSG labels. Labels are unverified user annotations; they are not resolved to operations.
- Fifty unranked direction entries across nine families. These are a research checklist, not predictions about the input material.
- Exact linear anomalous Hall constraints for supplied rational Cartesian magnetic point-group generators; finite closure capped at 96 operations. Illustrative presets are explicitly not material assignments.
- A certificate consisting of either an allowed Hall-vector witness or a rational row combination proving the requested component vanishes. Returned certificates are checked by substitution.
- An offline trace recording assumptions, the supported check, and conditional revision. This is a deterministic workflow, not an autonomous discovery or learned improvement.
- Optional single-call model planning through the existing provider adapter. Model text is an unverified proposal alongside immutable deterministic evidence. No external tool execution is granted to the model.
- JSON export; responsive page; preserved same-origin and local request-token protection.

## Connect the teammate's API via CC Switch

1. Configure the teammate's real upstream endpoint and key inside CC Switch. Review the provider's data handling and actual supported model IDs. No relay key belongs in source or shared archives.
2. For CC Switch, configure Codex-compatible local routing on `127.0.0.1:15721`; the client-facing protocol is Responses. Select the upstream protocol actually supported by the provider in CC Switch. Routing may rewrite local Codex client configuration, so review and back up the relevant settings first.
3. In the Material Explorer connection panel, select **CC Switch local routing**, keep Base URL `http://127.0.0.1:15721/v1`, select **Responses**, and enter the actual upstream model ID or its configured mapping.
4. Click **Test connection**. This makes one small real request. Then click **Generate model proposals** to send the current material profile, supplied Hall result and direction catalog. Each planning click makes one request capped at 1600 output tokens; this is not a dollar spending limit.
5. If the relay supports Chat Completions directly, **Custom compatible API** can instead use its HTTPS Base URL and **Chat Completions**. Set `SYMMETRYLAB_API_KEY` locally in the environment that starts the server. The browser accepts only the environment variable's name, never the key value. For this mode CC Switch is optional.

`config/materials-relay.example.json` is a connection-only preset accepted by `serve --config`. Replace its placeholder model ID before testing. API configuration is shared in server memory with the original workbench; do not run competing connection probes or research jobs.

The initial handoff used simulated providers. A subsequent local setup on 2026-10-22 successfully tested a short Responses generation against the user's relay and requested model. Private credentials and local launch settings remain outside the source and handoff archive. The client sends a SymmetryLab User-Agent and allows 60 seconds for relay responses. Installing CC Switch does not provide a key, balance or a working route.

That live result is reported by the sender. The receiving macOS integration reran the automated suite, not the live upstream request. The direct-relay result does not by itself validate CC Switch forwarding on another machine.

## SSG and literature extension contracts

`tools/materials.py` provides two replacement boundaries:

```python
SSGAdapter.lookup(material, conditions)
# {status, records, message}; every record should carry phase, temperature/field,
# structure provenance, group convention/setting, and magnetic moments/coordinates.

LiteratureAdapter.search(material, phenomenon)
# {status, papers, search_url, message}; papers should carry DOI/URL, title,
# exact evidence location, mechanism, conditions, and retrieval timestamp.
```

Pass adapter instances to `explore_material`. An implementation must explicitly wire them into the server's exploration path and, if desired, planning path. The current defaults return `not_connected`; there is no hidden download, database lookup, automatic group assignment, or fabricated citation. Literature buttons open external searches; they are not retrieval results. The verified-paper count intentionally remains zero until an evidence-review implementation exists.

Keep independent spin rotations in SSG distinct from real-space MSG operations. Do not feed an SSG label or spin-only matrices into the Hall checker. For a uniform response, reduce a validated appropriate physical symmetry to its point operations. The checker expects orthogonal Cartesian matrices, not matrices in a fractional lattice basis. For direct lattice columns L, transform a fractional direct-space operation W as R = L W L^-1. This exact prototype excludes operations needing irrational Cartesian entries. Incommensurate magnetic superspace structures need additional treatment.

## Hall rule and scope

For a uniform, zero-field, linear anomalous Hall response, the Hall pseudovector obeys `h = (-1)^t det(R) R h`, with `t` the antiunitary/time-reversal flag. Solve the homogeneous constraints for every supplied operation. Allowed means the component need not vanish by this symmetry; it does not establish a finite, large, novel or measurable response. Forbidden applies only to this component and the supplied complete physical symmetry assumptions. Neither result settles nonlinear Hall, field-induced Hall, TMR or other catalog directions. A second/third harmonic voltage alone does not identify a nonlinear Hall mechanism.

The illustrative revision compares C2z combined with time reversal (h_z forbidden) with an identity-only assumption (h_z allowed). No strain, field, phase transition or material realization of that assumption change is established.

Primary method reference: https://arxiv.org/abs/1507.04947
Magnetic structure source: https://cryst.ehu.es/magndata/
SSG reference: https://arxiv.org/abs/2307.10364

## Validation checkpoint

On the receiving development Windows environment, Python UTF-8 mode is needed for the legacy test that reads reports without an explicit encoding. With `PYTHONUTF8=1`, all **88 tests passed** after the extension (66 original plus 22 new parameterized cases/tests). Compilation and JavaScript syntax checks passed. Tests cover known axial-vector constraints, combined generators, independently checked certificates, unsupported closures, unverified material labels, unknown information, HTTP token protection, preserved legacy routes, and model-proposal/evidence separation with a simulated provider.

The sender delivered files because GitHub authentication was unavailable in their environment. The receiving integration verified the manifest and common baseline, imported the 15 changed paths, and reran all **88 tests** on macOS with Python 3.12.7. The original benchmark still returns **30/30** correct labels and **27/27** valid certificates. The original source delivery is retained outside the repository; its prebuilt wheel, preview image, and machine-specific assets were not imported.
