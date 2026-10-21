# Initial Demonstration Script

1. Verify T01: q=(1/2,0) is nonzero; an exact solution has first coordinate 1/4 or 3/4 and passes substitution.
2. Run the scripted demo. Identify the preset false conjecture and inspect PROPOSE, VERIFY, CRITIQUE, UPDATE_MEMORY, REVISE, RECHECK, and DONE in the trace.
3. Inspect T05: each generator is individually solvable, but the common system is not. Its certificate satisfies wB=0 and wq=1/2.
4. Open report_researcher_en.md, report_student_en.md, and report_general_en.md. Confirm the shared result_id and evidence hash.
5. Use --mode replay --source with that run directory to recheck the recorded result.
6. Show the actual 30-case evaluation metrics. Explain that these measure the verifier on public toys; real-API ablations, physical realization, novelty, and weight training remain unfinished.

## Graphical v0.2 demonstration

1. Run `.venv/bin/python -m symmetrylab serve` and open http://127.0.0.1:8787.
2. Keep **Offline demonstration** selected and click **Start research**. Explain that its policy is simulated and mathematical tools are real.
3. Show the plan and the first hypothesis, then the certified inversion counterexample.
4. Show retained feedback, the revised hypothesis and the translation obstruction.
5. Inspect exact candidate data; switch the report audience and download Markdown/JSON.
6. Expand **Model connection** to show the CC Switch preset. For an actual live demo, first enable local Codex routing, enter a supported model ID and pass **Test connection**. Then switch to **Live model research**. Do not describe the offline demonstration as real model evidence.
