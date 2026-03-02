---
name: beads
description: "Local-first issue tracker using br (beads_rust). Use when the user wants to track issues, create tasks, manage dependencies between issues, or check what's ready to work on. Triggers on: 'create an issue', 'track a bug', 'what should I work on next', 'show blocked issues', 'add a dependency', 'beads', 'br', or any project issue-tracking task."
---

# Beads (br) — Local-First Issue Tracker

A Rust CLI (`br`) that stores issues locally in SQLite. Lightweight, fast, dependency-aware.

Source: <https://github.com/Dicklesworthstone/beads_rust>

## Install

```bash
curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh?$(date +%s)" | bash
```

Or from source:

```bash
cargo install --git https://github.com/Dicklesworthstone/beads_rust.git
```

Verify: `br --version`

## Quick Start

```bash
br init                                    # Initialize in project root
br create "Fix login timeout" -p 1 --type bug
br ready                                   # Show actionable (unblocked) issues
br update bd-abc123 --status in_progress   # Claim work
br close bd-abc123 --reason "Fixed"        # Complete
```

## Storage

```
.beads/
├── beads.db        # SQLite (primary storage)
├── config.yaml     # Project configuration
└── metadata.json   # Workspace metadata
```

All data lives in `.beads/beads.db`. No daemons, no hooks, no background processes.

## Commands

### Issue Lifecycle

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize workspace | `br init` |
| `create` | Create issue | `br create "Title" -p 1 --type bug` |
| `q` | Quick capture (ID only) | `br q "Fix typo"` |
| `show` | Show issue details | `br show bd-abc123` |
| `update` | Update issue fields | `br update bd-abc123 --priority 0` |
| `close` | Close issue | `br close bd-abc123 --reason "Done"` |
| `reopen` | Reopen closed issue | `br reopen bd-abc123` |
| `delete` | Delete issue (tombstone) | `br delete bd-abc123` |

### Querying

| Command | Description | Example |
|---------|-------------|---------|
| `list` | List issues with filters | `br list --status open --priority 0-1` |
| `ready` | Actionable work (unblocked) | `br ready` |
| `blocked` | Blocked issues | `br blocked` |
| `search` | Full-text search | `br search "authentication"` |
| `stale` | Stale issues | `br stale --days 30` |
| `count` | Count with grouping | `br count --by status` |

### Dependencies

| Command | Description | Example |
|---------|-------------|---------|
| `dep add` | Add dependency (child blocked by parent) | `br dep add bd-child bd-parent` |
| `dep remove` | Remove dependency | `br dep remove bd-child bd-parent` |
| `dep list` | List dependencies | `br dep list bd-abc123` |
| `dep tree` | Dependency tree | `br dep tree bd-abc123` |
| `dep cycles` | Find cycles | `br dep cycles` |

### Labels & Comments

```bash
br label add bd-abc123 backend urgent    # Add labels
br label remove bd-abc123 urgent         # Remove label
br label list-all                        # All labels in project
br comments add bd-abc123 "Root cause found"
br comments list bd-abc123
```

### System

```bash
br doctor                  # Run diagnostics
br stats                   # Project statistics
br config --list           # Show config
br upgrade                 # Self-update
```

## Priority Levels

| Priority | Meaning |
|----------|---------|
| 0 | Critical |
| 1 | High |
| 2 | Normal (default) |
| 3 | Low |
| 4 | Backlog |

## Issue Types

`bug`, `feature`, `task`, `chore`, `epic`

## JSON Output (Agent-Friendly)

Every command supports `--json` for structured machine-readable output:

```bash
br list --json
br ready --json
br show bd-abc123 --json
br create "Title" --json       # Returns created issue as JSON
```

Schema discovery:

```bash
br schema all --format json
br schema issue-details --format toon   # Token-efficient
```

## Configuration

Layered (highest to lowest priority): CLI flags → env vars → `.beads/config.yaml` → `~/.config/beads/config.yaml` → defaults.

```yaml
# .beads/config.yaml
id:
  prefix: "proj"          # Custom ID prefix (default: "bd")
defaults:
  priority: 2
  type: "task"
  assignee: "team@example.com"
sync:
  auto_import: false
  auto_flush: false   # Keep sync disabled for local-only use
```

```bash
br config --set id.prefix=myproj
br config --set defaults.priority=1
br config --edit                      # Open in editor
```

| Env Variable | Description |
|--------------|-------------|
| `BEADS_DB` | Override database path |
| `RUST_LOG` | Logging level |

## Typical Workflow

```bash
# 1. Create issues with dependencies
br create "Implement user auth" --type feature -p 1       # → bd-7f3a2c
br create "Set up database schema" --type task -p 1        # → bd-e9b1d4
br dep add bd-7f3a2c bd-e9b1d4                             # auth blocked by schema

# 2. Work on what's ready
br ready                          # Shows bd-e9b1d4 (unblocked)
br update bd-e9b1d4 --status in_progress

# 3. Complete and unblock downstream
br close bd-e9b1d4 --reason "Schema implemented"
br ready                          # Now shows bd-7f3a2c
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| Database locked | Check for other `br` processes: `pgrep -f "br "` |
| Issue not found | Verify ID: `br list --json \| jq '.[] \| select(.id == "bd-abc123")'` |
| Prefix mismatch | Check prefix: `br config --get id.prefix` |
| Stale database | Run `br doctor` to diagnose |
| Garbled output | Use `br list --no-color` or `br list --json` |
