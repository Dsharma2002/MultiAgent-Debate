"""
CLI — Command-line interface for the Multi-Agent Debate framework.

Provides commands to:
- Run the full pipeline
- Verify ledger integrity
- List configured agents
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from mad.ledger.json_file import JsonFileLedger
from mad.ledger.integrity import verify_chain, detect_tampering
from mad.pipeline.orchestrator import PipelineOrchestrator
from mad.schemas.evidence import EvidenceEntry

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """MAD — Multi-Agent Debate Framework

    A decentralized multi-agent system with a Verified Common-Ground Layer.
    """
    setup_logging(verbose)


@cli.command()
@click.option(
    "--config",
    "-c",
    default="config",
    help="Path to config directory (contains agents.yaml, vocabulary.yaml, constraints.yaml)",
)
@click.option(
    "--task",
    "-t",
    required=True,
    help="Task description for the agents to evaluate",
)
@click.option(
    "--budget",
    "-b",
    default=1000,
    type=int,
    help="Budget allocation in USD",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output ledger file path (JSONL)",
)
@click.option(
    "--proposal-id",
    default=None,
    help="Custom proposal UUID (auto-generated if not provided)",
)
def run(
    config: str,
    task: str,
    budget: int,
    output: str | None,
    proposal_id: str | None,
) -> None:
    """Run the full multi-agent pipeline on a task."""
    console.print(
        Panel(
            f"[bold cyan]Multi-Agent Debate Pipeline[/bold cyan]\n"
            f"Task: {task}\n"
            f"Budget: ${budget:,}\n"
            f"Config: {config}/",
            title="🚀 Pipeline Start",
            border_style="cyan",
        )
    )

    # Build context
    context: dict[str, Any] = {
        "proposal_id": proposal_id or str(uuid4()),
        "description": task,
        "budget_allocation": budget,
    }

    # Setup ledger
    if output:
        from mad.ledger.json_file import JsonFileLedger
        ledger = JsonFileLedger(output)
    else:
        from mad.ledger.memory import InMemoryLedger
        ledger = InMemoryLedger()

    # Create and run pipeline
    try:
        orchestrator = PipelineOrchestrator.from_config(
            config_dir=config,
            ledger=ledger,
        )
        result = orchestrator.run(context)
    except Exception as e:
        console.print(f"[bold red]Pipeline error:[/bold red] {e}")
        raise SystemExit(1)

    # Display results
    _display_pipeline_result(result)

    # Save output if using file ledger
    if output:
        console.print(f"\n[green]Ledger saved to:[/green] {output}")


@cli.command(name="verify-ledger")
@click.argument("ledger_file")
def verify_ledger(ledger_file: str) -> None:
    """Verify the hash-chain integrity of a ledger file."""
    path = Path(ledger_file)
    if not path.exists():
        console.print(f"[bold red]File not found:[/bold red] {ledger_file}")
        raise SystemExit(1)

    console.print(f"[cyan]Verifying ledger:[/cyan] {ledger_file}")

    # Load and verify
    try:
        ledger = JsonFileLedger(ledger_file)
    except ValueError as e:
        console.print(f"[bold red]Parse error:[/bold red] {e}")
        raise SystemExit(1)

    entries = ledger.get_all()
    is_valid, errors = verify_chain(entries)
    tampered = detect_tampering(entries)

    # Display results
    table = Table(title="Ledger Integrity Report")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green" if is_valid else "red")

    table.add_row("Total entries", str(len(entries)))
    table.add_row("Verified entries", str(sum(1 for e in entries if e.verified_status)))
    table.add_row("Chain valid", "✅ Yes" if is_valid else "❌ No")
    table.add_row("Tampered entries", str(len(tampered)))

    console.print(table)

    if errors:
        console.print("\n[bold red]Integrity Errors:[/bold red]")
        for err in errors:
            console.print(f"  ❌ {err}")

    if tampered:
        console.print("\n[bold red]Tampered Entries:[/bold red]")
        for t in tampered:
            console.print(
                f"  ⚠️  Entry {t['index']} ({t['entry_id'][:8]}...): "
                f"{', '.join(t['issues'])}"
            )

    raise SystemExit(0 if is_valid else 1)


@cli.command(name="list-agents")
@click.option(
    "--config",
    "-c",
    default="config",
    help="Path to config directory",
)
def list_agents(config: str) -> None:
    """List all configured agents and their specialties."""
    import yaml

    agents_path = f"{config}/agents.yaml"
    try:
        with open(agents_path, "r") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        console.print(f"[bold red]Config not found:[/bold red] {agents_path}")
        raise SystemExit(1)

    table = Table(title="Configured Agents")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Core Specialty (70%)", style="yellow")
    table.add_column("Audit Constraints (30%)", style="magenta")

    for agent in data.get("agents", []):
        table.add_row(
            agent["agent_id"],
            agent.get("name", ""),
            agent.get("core_specialty", "")[:60] + "...",
            ", ".join(agent.get("audit_constraints", [])),
        )

    console.print(table)

    # Show pipeline config
    pipeline = data.get("pipeline", {})
    if pipeline:
        console.print(
            Panel(
                f"Execution Order: {' → '.join(pipeline.get('execution_order', []))}\n"
                f"Min Peer Validations: {pipeline.get('min_peer_validations', 2)}\n"
                f"Max Retry on Reject: {pipeline.get('max_retry_on_reject', 1)}",
                title="📋 Pipeline Configuration",
                border_style="blue",
            )
        )


def _display_pipeline_result(result) -> None:
    """Display pipeline results with rich formatting."""
    # Step results table
    table = Table(title="Pipeline Execution Results")
    table.add_column("Step", style="cyan")
    table.add_column("Agent", style="green")
    table.add_column("Status", no_wrap=True)
    table.add_column("Attempts", justify="center")
    table.add_column("Peer Approvals", justify="center")

    for i, step in enumerate(result.step_results, 1):
        status = "[bold green]✅ COMMITTED[/bold green]" if step.success else "[bold red]❌ REJECTED[/bold red]"
        approvals = str(step.gate_result.peer_validation_count)
        table.add_row(str(i), step.agent_name, status, str(step.attempt), approvals)

    console.print(table)

    # Ledger snapshot
    if result.ledger_snapshot:
        snap = result.ledger_snapshot
        console.print(
            Panel(
                f"Total Entries: {snap.total_entries}\n"
                f"Verified Entries: {snap.verified_entries}\n"
                f"Chain Valid: {'✅' if snap.chain_valid else '❌'}",
                title="📒 Truth Ledger Snapshot",
                border_style="green" if snap.chain_valid else "red",
            )
        )

    # Overall status
    if result.success:
        console.print("\n[bold green]✅ PIPELINE COMPLETED SUCCESSFULLY[/bold green]")
    else:
        console.print("\n[bold red]❌ PIPELINE COMPLETED WITH ERRORS[/bold red]")
        for err in result.errors:
            console.print(f"  → {err}")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
