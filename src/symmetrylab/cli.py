"""Offline-first CLI. No API calls unless --mode live is explicitly selected."""

import argparse
import json
from pathlib import Path
from symmetrylab.schemas import read_json, write_json, SolverBudget
from symmetrylab.verifier.gauge_solver import solve_gauge_equivalence
from symmetrylab.verifier.certificate import verify_certificate
from symmetrylab.evaluation.benchmark import evaluate, load_suite
from symmetrylab.agent_core.research_loop import run_research


def main(argv=None):
    parser = argparse.ArgumentParser(prog="symmetrylab", description="SymmetryLab — a verifiable symmetry research prototype")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="Verify a common gauge problem using exact arithmetic")
    verify.add_argument("case")
    verify.add_argument("--output")
    verify.add_argument("--seconds", type=float, default=10)
    verify.add_argument("--max-combinations", type=int, default=100000)
    demo = sub.add_parser("demo", help="Run a controlled demo, replay a result, or run constrained live research")
    demo.add_argument("--mode", choices=["scripted", "replay", "live"], default="scripted")
    demo.add_argument("--suite", default="benchmarks/manifest.json")
    demo.add_argument("--output", required=True)
    demo.add_argument("--source")
    demo.add_argument("--config")
    demo.add_argument("--predicate", choices=["nonzero_q_implies_nontrivial", "individual_implies_joint"],
                      default="nonzero_q_implies_nontrivial")
    ev = sub.add_parser("evaluate", help="Evaluate the frozen benchmark with the deterministic verifier")
    ev.add_argument("--suite", default="benchmarks/manifest.json")
    ev.add_argument("--output", required=True)
    research = sub.add_parser("research", help="Run iterative model-driven research or the simulated policy")
    research.add_argument("--mode", choices=["demo", "live"], default="demo")
    research.add_argument("--goal", required=True)
    research.add_argument("--output", required=True)
    research.add_argument("--config")
    web = sub.add_parser("serve", help="Open the local English research workbench")
    web.add_argument("--port", type=int, default=8787)
    web.add_argument("--data", default="data/workbench")
    web.add_argument("--config")
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            from symmetrylab.web.server import serve
            serve(args.port, args.data, read_json(args.config) if args.config else None)
            return 0
        if args.command == "research":
            from symmetrylab.agent_core.workbench import run_agent
            result = run_agent(args.goal, args.output, args.mode, read_json(args.config) if args.config else None)
            print(json.dumps({"run_id": result["run_id"], "status": result["status"], "metrics": result["metrics"]}, indent=2))
            return 0 if result["status"] == "completed" else 2
        if args.command == "verify":
            case = read_json(args.case)
            result = solve_gauge_equivalence(case, budget=SolverBudget(args.max_combinations, args.seconds))
            result["certificate_verified"] = verify_certificate(case, result) if result["status"] in {"gauge_trivial", "gauge_nontrivial"} else None
            if args.output:
                if Path(args.output).exists():
                    raise ValueError("output file already exists")
                write_json(args.output, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("certificate_verified") is True else 2
        if args.command == "evaluate":
            metrics = evaluate(args.suite, args.output)
            print(json.dumps(metrics, ensure_ascii=False, indent=2))
            return 0 if metrics["total"] > 0 and metrics["correct"] == metrics["total"] else 1
        config = read_json(args.config) if args.config else {}
        client = None
        if args.mode == "live":
            from symmetrylab.model.client import OpenAICompatibleClient
            client = OpenAICompatibleClient(config)
        # Demo reads only golden inputs, never dev/held-out answers.
        cases = [] if args.mode == "replay" else [case for case, _ in load_suite(args.suite, split="golden")]
        result = run_research(cases, args.output, args.mode, config, client,
                              source=args.source, predicate=args.predicate)
        print(json.dumps({"mode": args.mode, "result_id": result["result_id"],
                          "status": result["hypothesis_status"], "output": str(Path(args.output).resolve())},
                         ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        # CLI errors never include configuration or credentials.
        print(f"SymmetryLab: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
