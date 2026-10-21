# Privacy and Execution Boundaries

Version 0.2 supports public_toy inputs only. Existing private SSG papers, databases, and Mathematica code are not connected. Direct-provider API keys come from environment variables and are excluded from configuration, source files, and logs. Git ignores data/ by default.

Live mode sends only public toys, exact tool results, and current-run lessons to the user-configured provider. It does not automatically upload files or read another project's authentication data. Model output is parsed as allowlisted JSON and is never executed as code. HTTPS redirects are disabled to prevent credentials from being forwarded to an unexpected destination.

MCP and cross-run memory retrieval are not connected. Local run persistence is implemented. The research loop has no tool for modifying source code, tests, rewards, or permissions. Public releases, official competition submissions, and transmission of real research data require explicit authorization from the researcher. Logs do not collect hidden chains of thought.

CC Switch mode connects only to an explicit loopback URL and uses a placeholder credential. The local proxy manages the real provider key. SymmetryLab never opens `cc-switch.db`, Codex authentication files, or private research files. Plain HTTP is accepted only for loopback connections; other endpoints require HTTPS. Local routing bypasses unrelated system HTTP proxies. Redirects are always rejected.

The browser sends only public connection fields, not an API key. Live research transmits the user-entered goal, candidates, observations and current-run memory. Users must keep these inputs public. The HTTP workbench binds to 127.0.0.1, validates Host and Origin, rejects cross-site requests, and requires a per-server request token for mutations. Static assets are local and model text is rendered with textContent. There is no public deployment or multi-user authentication in this release.
