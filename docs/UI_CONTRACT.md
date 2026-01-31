# BLUX App UI Contract (Phase 1)

Phase 1 defines the UI shape for a **read-only** viewer. The app does **not**
execute, orchestrate, or enforce anything. It only renders artifacts that are
already produced elsewhere.

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

### Build Artifact Panel (cA output)
Shows the cA build artifact, as-is.

- **Source**: `ca.json`
- **Accepted input**: file path or JSON payload
- **Suggested fields**:
  - `summary`: string
  - `outputs`: array/object
  - `files`: optional array of file descriptors

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

### Execution Receipt Panel (System Snapshot Reference)
Shows a receipt for the execution environment (snapshots or references only).

- **Source**: `receipt.json`
- **Accepted input**: file path or JSON payload
- **Suggested fields**:
  - `system_snapshot_ref`: string
  - `timestamp`: string (ISO-8601 recommended)
  - `metadata`: optional object

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

Missing files are allowed and should be reported as absent panels.
