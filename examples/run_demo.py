#!/usr/bin/env python3
"""
End-to-end demo of the Multi-Agent Debate pipeline.

This script demonstrates:
1. Loading configuration from YAML files
2. Running the full 4-agent pipeline
3. Verification Gate in action (vocabulary, constraints, peer audit)
4. Ledger integrity verification
5. Rich terminal output of results

Usage:
    python examples/run_demo.py
    python examples/run_demo.py --output demo_ledger.jsonl
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from uuid import uuid4

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from mad.ledger.memory import InMemoryLedger
from mad.ledger.integrity import verify_chain, detect_tampering
from mad.pipeline.orchestrator import PipelineOrchestrator

console = Console()


def run_demo(output_file: str | None = None) -> None:
    """Run the complete demo scenario."""

    # ── Setup Logging ─────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    # ── Banner ────────────────────────────────────────────────────────────
    console.print(
        Panel(
            "[bold cyan]Multi-Agent Debate Framework[/bold cyan]\n"
            "[dim]Decentralized Verification Pipeline Demo[/dim]\n\n"
            "This demo runs a proposal through 4 specialized agents:\n"
            "  1. Tech Lead → Technical feasibility assessment\n"
            "  2. Product Manager → Business value & ROI analysis\n"
            "  3. QA Engineer → Edge-case & risk identification\n"
            "  4. Security Auditor → Threat modeling & compliance\n\n"
            "Each agent's output passes through the Verification Gate\n"
            "with vocabulary checks, constraint validation, and peer audit.",
            title="🧪 Demo Scenario",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # ── Create Pipeline ───────────────────────────────────────────────────
    config_dir = str(Path(__file__).parent.parent / "config")

    if output_file:
        from mad.ledger.json_file import JsonFileLedger
        ledger = JsonFileLedger(output_file)
    else:
        ledger = InMemoryLedger()

    orchestrator = PipelineOrchestrator.from_config(
        config_dir=config_dir,
        ledger=ledger,
    )

    # ── Define Task Context ───────────────────────────────────────────────
    context = {
        "proposal_id": str(uuid4()),
        "description": (
            "Build a real-time notification system with WebSocket support, "
            "user preference management, and API rate limiting. "
            "Requires database schema for notification storage and "
            "authentication integration."
        ),
        "budget_allocation": 2500,
        "complexity": "high",
        "user_impact": "high",
        "effort": "medium",
        "database": "PostgreSQL v15 with TimescaleDB extension",
        "scale_requirements": "10,000 concurrent WebSocket connections",
    }

    console.print(
        Panel(
            f"[bold]Proposal ID:[/bold] {context['proposal_id']}\n"
            f"[bold]Description:[/bold] {context['description'][:100]}...\n"
            f"[bold]Budget:[/bold] ${context['budget_allocation']:,}\n"
            f"[bold]Complexity:[/bold] {context['complexity']}\n"
            f"[bold]User Impact:[/bold] {context['user_impact']}",
            title="📋 Task Context",
            border_style="yellow",
        )
    )

    # ── Run Pipeline ──────────────────────────────────────────────────────
    console.print("\n[bold cyan]Running pipeline...[/bold cyan]\n")
    result = orchestrator.run(context)

    # ── Display Results ───────────────────────────────────────────────────
    console.print("\n")

    # Step results
    table = Table(title="📊 Pipeline Execution Results", show_lines=True)
    table.add_column("Step", style="cyan", justify="center", width=6)
    table.add_column("Agent", style="green", width=20)
    table.add_column("Status", width=15, no_wrap=True)
    table.add_column("Attempts", justify="center", width=10)
    table.add_column("Peer Approvals", justify="center", width=16)

    for i, step in enumerate(result.step_results, 1):
        if step.success:
            status = "[bold green]✅ COMMITTED"
        else:
            status = "[bold red]❌ REJECTED"
        table.add_row(
            str(i),
            step.agent_name,
            status,
            str(step.attempt),
            str(step.gate_result.peer_validation_count),
        )

    console.print(table)

    # Ledger details
    if result.ledger_snapshot:
        snap = result.ledger_snapshot

        console.print(
            Panel(
                f"Total Entries: {snap.total_entries}\n"
                f"Verified Entries: {snap.verified_entries}\n"
                f"Chain Valid: {'✅ Yes' if snap.chain_valid else '❌ No'}\n"
                f"Total Budget Used: ${ledger.get_total_budget():,}",
                title="📒 Truth Ledger Summary",
                border_style="green" if snap.chain_valid else "red",
            )
        )

        # Show individual entries
        if snap.entries:
            entries_table = Table(title="📝 Ledger Entries", show_lines=True)
            entries_table.add_column("#", style="dim", width=4)
            entries_table.add_column("Agent", style="cyan", width=18)
            entries_table.add_column("Type", style="yellow", width=22)
            entries_table.add_column("Budget", justify="right", width=10)
            entries_table.add_column("Verified", justify="center", width=10)
            entries_table.add_column("Hash (first 16)", style="dim", width=18)

            for i, entry in enumerate(snap.entries):
                entries_table.add_row(
                    str(i),
                    entry.author_agent_id,
                    entry.content.get("assessment_type", "unknown"),
                    f"${entry.content.get('budget_allocation', 0):,}",
                    "✅" if entry.verified_status else "❌",
                    entry.entry_hash[:16] + "...",
                )

            console.print(entries_table)

    # Integrity verification
    console.print("\n[bold cyan]Running integrity verification...[/bold cyan]")
    entries = ledger.get_all()
    is_valid, errors = verify_chain(entries)
    tampered = detect_tampering(entries)

    if is_valid:
        console.print("[bold green]✅ Hash chain integrity verified![/bold green]")
    else:
        console.print("[bold red]❌ Hash chain integrity FAILED![/bold red]")
        for err in errors:
            console.print(f"  → {err}")

    if tampered:
        console.print(f"[bold red]⚠️  {len(tampered)} tampered entries detected[/bold red]")

    # Final status
    console.print(
        Panel(
            f"Pipeline: {'[bold green]SUCCESS' if result.success else '[bold red]PARTIAL FAILURE'}\n"
            f"Committed: {result.committed_count}/{len(result.step_results)}\n"
            f"Failed: {result.failed_count}/{len(result.step_results)}\n"
            f"Chain Valid: {'✅' if is_valid else '❌'}",
            title="🏁 Final Status",
            border_style="green" if result.success else "yellow",
        )
    )

    if output_file:
        console.print(f"\n[green]Ledger saved to:[/green] {output_file}")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("--output") else None
    if output and "=" in output:
        output = output.split("=")[1]
    elif len(sys.argv) > 2 and sys.argv[1] == "--output":
        output = sys.argv[2]
    run_demo(output)
