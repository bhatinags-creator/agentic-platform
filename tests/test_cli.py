from sdk.python.agentic_platform_client.cli import build_parser


def test_cli_parser_parses_start_run_command() -> None:
    parser = build_parser()

    args = parser.parse_args([
        "--tenant-id",
        "tenant-a",
        "start-run",
        "--user-id",
        "user-1",
        "--agent-id",
        "agent.support",
        "--agent-version",
        "1.0.0",
        "--input-json",
        '{"message":"hello"}',
    ])

    assert args.command == "start-run"
    assert args.tenant_id == "tenant-a"
    assert args.agent_id == "agent.support"


def test_cli_parser_parses_metrics_command() -> None:
    parser = build_parser()

    args = parser.parse_args(["metrics"])

    assert args.command == "metrics"
    assert args.runtime_url == "http://localhost:8002"
