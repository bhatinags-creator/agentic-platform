from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from sdk.python.agentic_platform_client.client import AgenticPlatformClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic-platform", description="Agentic Platform CLI")
    parser.add_argument("--control-plane-url", default="http://localhost:8001")
    parser.add_argument("--runtime-url", default="http://localhost:8002")
    parser.add_argument("--tenant-id", default="default")
    subcommands = parser.add_subparsers(dest="command", required=True)

    create_agent = subcommands.add_parser("create-agent")
    create_agent.add_argument("--name", required=True)
    create_agent.add_argument("--owner", required=True)
    create_agent.add_argument("--risk-class", default="medium")

    subcommands.add_parser("list-agents")

    start_run = subcommands.add_parser("start-run")
    start_run.add_argument("--user-id", required=True)
    start_run.add_argument("--agent-id", required=True)
    start_run.add_argument("--agent-version", required=True)
    start_run.add_argument("--input-json", default="{}")

    get_run = subcommands.add_parser("get-run")
    get_run.add_argument("--run-id", required=True)

    subcommands.add_parser("list-runs")
    subcommands.add_parser("metrics")
    subcommands.add_parser("list-drafts")
    return parser


async def run_command(args: argparse.Namespace) -> dict[str, Any]:
    client = AgenticPlatformClient(
        control_plane_url=args.control_plane_url,
        runtime_url=args.runtime_url,
        tenant_id=args.tenant_id,
    )
    match args.command:
        case "create-agent":
            return await client.create_agent(
                name=args.name,
                owner=args.owner,
                risk_class=args.risk_class,
            )
        case "list-agents":
            return await client.list_agents()
        case "start-run":
            payload = {
                "user_id": args.user_id,
                "agent_id": args.agent_id,
                "agent_version": args.agent_version,
                "input": json.loads(args.input_json),
            }
            return await client.start_run(payload)
        case "get-run":
            return await client.get_run(args.run_id)
        case "list-runs":
            return await client.list_runs()
        case "metrics":
            return await client.get_metrics()
        case "list-drafts":
            return await client.list_agent_drafts()
    raise ValueError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = asyncio.run(run_command(args))
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
