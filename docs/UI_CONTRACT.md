# BLUX App UI Contract (V1.0)

BLUX App is a **read-only** viewer. It never executes, orchestrates, or mutates
artifacts. It only renders JSON files already produced elsewhere.

## Panels

### Intent Panel (ProblemSpec / GoalSpec)
Displays the user intent inputs that started the run.

- **Source**: `intent.json`
- **Accepted input**: file path or JSON payload
- **Suggested fields**:
  - `problem_spec`: string or structured object
  - `goal_spec`: string or structured object
  - `constraints`: optional array/object

### Reasoning Artifact Panel (CogA output)
Shows the CogA reasoning artifact, as-is.

- **Source**: `coga.json`
- **Accepted input**: file path or JSON payload
- **Suggested fields**:
  - `summary`: string
  - `artifacts`: array/object
  - `trace`: optional array/object
  - `options`: optional list
  - `comparison_matrix`: optional object
  - `reasoning_pack`: optional object with `id` + `version`

### Build Artifact Panel (cA output)
Shows the cA build artifact, as-is.

- **Source**: `ca.json`
- **Accepted input**: file path or JSON payload
- **Suggested fields**:
  - `summary`: string
  - `outputs`: array/object
  - `files`: optional array of file descriptors
  - `patch_bundle`: optional unified diff
  - `policy_pack`: optional object with `id` + `version`

### Verdict Panel(s)
Shows verdicts or checks produced by downstream tooling.

- **Source**: `verdicts.json`
- **Accepted input**: file path or JSON payload
- **Suggested fields**:
  - `verdicts`: array of objects, each with:
    - `id`: string
    - `status`: string (e.g., `pass`, `warn`, `fail`)
    - `message`: string
    - `details`: optional object

### Execution Receipt Panel (Agent)
Shows a receipt for the agent run (snapshots or references only).

- **Source**: `receipt.json`
- **Accepted input**: file path or JSON payload
- **Suggested fields**:
  - `system_snapshot_ref`: string
  - `timestamp`: string (ISO-8601 recommended)
  - `agent_runs`: optional array of run objects
  - `versions`: optional object
  - `hashes`: optional object
  - `steps` / `run_graph`: optional run graph
  - `fixtures`: optional fixture references

### Execution Receipt Panel (System)
Shows system-level receipts or environment metadata.

- **Source**: `execution_receipt.json`
- **Accepted input**: file path or JSON payload

### Replay Report Panel
Shows replay and verification results from a harness or auditor.

- **Source**: `replay_report.json`
- **Accepted input**: file path or JSON payload

### Acceptance Report Panel
Shows acceptance verdicts for cA / CogA outputs.

- **Source**: `accept_report.json`
- **Accepted input**: file path or JSON payload

### Harness Report Panel
Shows harness summary + per-fixture results.

- **Source**: `report.json`
- **Accepted input**: file path or JSON payload

### Raw JSON Panels
Any extra `*.json` files in the run directory are rendered as a fallback panel.

## UI Behaviors

- **Pack headers**: When `reasoning_pack` or `policy_pack` metadata is present,
  their `id`/`version` values appear in the panel header.
- **Run graphs**: If a receipt includes steps / nodes, a timeline list renders
  status, ids, hashes, and timestamps.
- **Version negotiation**: Requested vs resolved versions render per run.
- **Dataset linkage**: Fixture IDs and hashes render with verification badges
  (`verified`, `mismatch`, `unknown`) derived from `replay_report.json`.
- **Forward compatible**: unknown fields are preserved and rendered as JSON.

## Input Rules

- **Only** file paths or JSON payloads are accepted inputs.
- **No** network access, subprocess execution, or orchestration is permitted.
- The viewer must render JSON verbatim (or minimally formatted) without
  transforming or mutating content.

## Directory Layout (Default)

When a directory is supplied, the viewer resolves the following files:

- `intent.json`
- `coga.json`
- `ca.json`
- `verdicts.json`
- `receipt.json`
- `execution_receipt.json`
- `replay_report.json`
- `accept_report.json`
- `report.json`

Missing files are allowed and should be reported as absent panels.
