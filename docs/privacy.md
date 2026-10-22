# Privacy and Execution Boundaries

The v0.3 preview supports public toy models, public scientific metadata and research context explicitly selected by the user. Private SSG papers, databases and Mathematica code are not automatically connected. No automatic paper-folder scan occurs.

## Selected context and model requests

Live mode sends the research brief, selected paper text, keywords, sample conditions, tool observations and recalled strategies to the configured model provider. Public searches send bounded queries to COD or Crossref. The web form states this before running. Use public or shareable material; publication, official submissions and transmission of additional private research require explicit researcher authorization.

Paper input accepts pasted text or a user-selected .txt/.md reading list. Full PDF ingestion is not implemented. Imported text and retrieved metadata are untrusted data, never executable instructions. Source retrieval uses fixed endpoints, bounded response sizes and no redirects. The model cannot fetch arbitrary URLs, read local files, execute code or modify its verifier, tests, rewards or access policy.

## Credentials and local server

Direct-provider API keys are read from environment variables. Only public connection settings reach the browser or configuration files; keys are not written to source or application logs. The user's explicitly authorized desktop-file launcher is local and outside the repository. Portable installations use the environment-variable workflow.

The API key entered on the Connection page is saved in `connection.json` beside the run data with permission 0600. It is not encrypted; anyone who can read your account files can read it. It is never returned to the interface or written to run records. Plain HTTP is accepted only for loopback connections; remote providers require HTTPS. Redirects are rejected. Local routing bypasses unrelated system HTTP proxies.

The workbench binds to 127.0.0.1, validates Host and Origin, rejects cross-site API requests and requires a per-server request token for mutations. Top-level navigation to the two HTML pages is permitted. Static assets are local; model content is rendered as text. The application has no public deployment or multi-user authentication.

## History, preferences and reuse

Run snapshots, source records, concise action rationales, evidence and reports are saved locally under data/. Hidden chains of thought are not requested or collected. Git ignores data/, local diagnostics under work/, environment files and databases. Review selected research context before sharing exported reports.

Cross-run strategy recall independently rechecks stored counterexamples and separates research tracks and demo/live records. It regenerates strategy text from checked evidence rather than trusting old model prose. Human preference feedback is saved separately in local JSONL and cannot change mathematical certificates. It is reused only with the same selected-paper context and track; when no papers are supplied, keywords must also match. Current user corrections take precedence. There is no automatic code modification or weight training.
