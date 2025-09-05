# Task 002: Configuration Loading

**Objective:** Implement the hierarchical configuration loading mechanism.

## Requirements

1.  **YAML Parsing:**
    *   Use a library like `PyYAML` to parse `.yaml` files.

2.  **Global Configuration:**
    *   The application must look for and load a global configuration file from `~/.tasak/tasak.yaml`.

3.  **Local Configuration (Hierarchical):**
    *   The application must search for local configuration files starting from the current working directory and moving upwards to the root.
    *   The search paths are: `./tasak.yaml`, `./.tasak/tasak.yaml`, `../tasak.yaml`, `../.tasak/tasak.yaml`, and so on.

4.  **Configuration Merging:**
    *   Implement a merging strategy:
        *   Start with the global configuration as the base.
        *   Iterate through the found local configurations (from the root of the filesystem down to the current directory) and merge them.
        *   The merge logic should be "last-in-wins": if a key exists in both the current merged config and a new config, the value from the new config should be used.

## Acceptance Criteria

*   A function exists that can successfully load and parse a YAML file.
*   The application correctly identifies and loads the global config file.
*   The application can find all local config files in a directory hierarchy.
*   The final, merged configuration correctly reflects the specified merging strategy.
