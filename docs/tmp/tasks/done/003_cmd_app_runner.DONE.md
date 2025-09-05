# Task 003: `cmd` App Runner

**Objective:** Implement a flexible runner for `cmd` applications with two distinct modes: `proxy` and `curated`.

## Core Requirements

1.  **App Discovery & Type Check:**
    *   Based on the loaded configuration and the app name provided as a command-line argument, find the corresponding app configuration.
    *   Verify that the app's `type` is `cmd`.

2.  **Mode Detection:**
    *   Check for a `meta.mode` field. It can be `proxy` or `curated`.
    *   If `meta.mode` is not specified, it should default to `proxy`.

3.  **Output Streaming:**
    *   For both modes, capture the `stdout` and `stderr` of the executed command and stream the output to the console in real-time.

---

## Mode 1: `proxy` (Default)

This mode directly forwards all arguments from `tasak` to the target command.

### Requirements

1.  **Command Construction:**
    *   Take the base `command` from `meta.command`.
    *   Append all positional and optional arguments passed to `tasak` after the app name.
    *   Example: `tasak my-git status --short` with `command: "git"` should execute `git status --short`.

2.  **Execution:**
    *   Use the `subprocess` module to execute the fully constructed command.

### `tasak.yaml` Example

```yaml
git:
  name: "Git Proxy"
  type: "cmd"
  meta:
    mode: "proxy" # This is the default, so it's optional
    command: "git"
```

---

## Mode 2: `curated`

This mode provides a structured interface by mapping `tasak` arguments to the target command's arguments.

### Requirements

1.  **Parameter Definition:**
    *   The runner must parse a `meta.params` list, where each item defines a parameter for the `tasak` CLI.
    *   Each parameter definition can include `name`, `maps_to`, `required`, `help`, `default`.

2.  **Argument Parsing:**
    *   Dynamically build a command-line argument parser (e.g., using `argparse`) based on the `meta.params` definition.
    *   Parse the arguments provided to `tasak` for the specific app.

3.  **Command Construction:**
    *   Construct the final command by mapping the parsed `tasak` arguments to the arguments of the target `command` as defined in `maps_to`.

### `tasak.yaml` Example

```yaml
docker_build:
  name: "Build Docker Image"
  type: "cmd"
  meta:
    mode: "curated"
    command: "docker build"
    params:
      - name: "--tag"
        maps_to: "-t"
        required: true
        help: "The tag for the Docker image (e.g., my-app:latest)."
      - name: "--path"
        maps_to: "."
        required: false
        default: "."
        help: "Path to the Dockerfile (defaults to current directory)."
```

---

## Acceptance Criteria

*   When a `cmd` app is called, it correctly identifies the mode (`proxy` or `curated`).
*   **Proxy mode:** `tasak my-app arg1 --arg2` correctly executes `[command] arg1 --arg2`.
*   **Curated mode:** `tasak my-app --tag latest` correctly executes `[command] -t latest` based on the `params` mapping.
*   **Curated mode:** Running `tasak my-app --help` displays a help message generated from the `params` definitions.
*   If a required argument in `curated` mode is missing, a clear error is shown.
*   If the app name does not exist, a clear error message is shown.
