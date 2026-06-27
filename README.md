# Multi-Agent Debate (MAD) Framework

A decentralized multi-agent system with a **Verified Common-Ground Layer**. Agents operate within strict specialty boundaries and communicate exclusively through an append-only, hash-chained **Truth Ledger**.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrator                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │Tech Lead │→ │Product   │→ │QA        │→ │Security      │ │
│  │  Agent   │  │Manager   │  │Engineer  │  │Auditor       │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
│       │              │              │               │         │
│       ▼              ▼              ▼               ▼         │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Verification Gate                         │   │
│  │  1. Vocabulary Check  →  2. Constraint Check          │   │
│  │  3. Peer Audit        →  4. COMMIT / REJECT           │   │
│  └────────────────────────┬───────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌────────────────────────────────────────────────────────┐   │
│  │           Truth Ledger (Append-Only)                   │   │
│  │  Hash-chained  •  Immutable  •  Tamper-detectable      │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Core Principles

1. **Isolation of Execution** — Agents operate strictly within their Specialty Core
2. **Task-Scoped Collaboration** — Communication via the Verified Common-Ground Layer only
3. **Immutable State** — All data passes an explicit verification step before entering the ledger

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# List configured agents
python -m mad.cli list-agents -c config

# Run the pipeline
python -m mad.cli run -c config -t "Build a notification system" -b 2000

# Run the demo
python examples/run_demo.py

# Verify ledger integrity
python -m mad.cli verify-ledger output_ledger.jsonl
```

## Agents

| Agent | Core Specialty (70%) | Audit Mandate (30%) |
|-------|---------------------|---------------------|
| **Tech Lead** | DB optimization, backend architecture | Constraint 01 (budget), 03 (peer validation) |
| **Product Manager** | Feature prioritization, ROI | Constraint 01 (budget) |
| **QA Engineer** | Edge-cases, test coverage | Constraint 03 (peer validation) |
| **Security Auditor** | Threat modeling, access control | Constraint 02 (security boundaries) |

## Shared Constraints

| ID | Rule | Severity |
|----|------|----------|
| `constraint_01` | Total budget ≤ $5,000 | Critical |
| `constraint_02` | QA cannot handle high-security data | Critical |
| `constraint_03` | Minimum 2 peer validations per entry | High |

## Verification Pipeline

Every entry follows this strict protocol:

1. **Local Draft** — Agent generates output within its specialty
2. **Structural Audit** — Vocabulary + constraint checks
3. **Verification Gate** — Peer agents cross-audit; REJECT loops once for correction
4. **Commit** — Entry added to ledger with `[Verified Status: True]`

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific suites
python -m pytest tests/test_schemas.py -v
python -m pytest tests/test_ledger.py -v
python -m pytest tests/test_constraints.py -v
python -m pytest tests/test_agents.py -v
python -m pytest tests/test_pipeline.py -v
python -m pytest tests/test_integration.py -v
```

## Configuration

All configuration lives in `config/`:
- `vocabulary.yaml` — Approved data keys and types
- `constraints.yaml` — Hard constraint metadata
- `agents.yaml` — Agent definitions and pipeline order

## License

MIT
