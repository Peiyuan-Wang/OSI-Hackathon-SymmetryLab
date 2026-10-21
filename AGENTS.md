# SymmetryLab Development Guide

Read `docs/implementation_plan.md`, `docs/mathematical_conventions.md`, and the relevant feature documentation before making changes.

- Use English for project-authored documentation, prompts, comments, CLI messages, and generated reports.
- Preserve the Newspaper src layout and dependency boundaries: agent_core owns the workflow; model/tools/mcp/memory provide implementations; database is the persistence boundary; verifier independently determines mathematical labels.
- Install, compile, and test with the current project's `.venv`. Python >=3.11 is required; the tested local version is recorded in implementation_status.
- Update the corresponding docs for each user-visible feature. Explicitly record incomplete work.
- Use public toy inputs. Do not automatically read private papers, databases, or another project's credentials.
- Nonzero q does not imply gauge nontriviality. Check group relations first, then solve for one theta shared by all generators.
- Substitute every exact solution back into the equations. An impossibility claim requires evidence. Budget exhaustion does not mean unsolvability; finite testing does not prove a general theorem.
- The research agent must not modify the verifier, expected test answers, scoring, or privacy configuration. Never execute model text as code.
- Report real experimental results. Identify scripted demonstrations and replays accurately.
- Do not create commits, push, or publish as part of ordinary development; these actions require an explicit user request.
- Validate with `.venv/bin/python -m compileall -q src tests`, `.venv/bin/python -m pytest -q`, and `git diff --check`.
