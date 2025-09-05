import os
from pathlib import Path
import yaml

def get_global_config_path() -> Path | None:
    """Returns the path to the global config file, if it exists."""
    home_dir = Path.home()
    config_path = home_dir / ".tasak" / "tasak.yaml"
    return config_path if config_path.exists() else None

def find_local_config_paths() -> list[Path]:
    """Finds all local config files by traversing up the directory tree."""
    search_paths = []
    current_dir = Path.cwd()

    while True:
        tasak_yaml = current_dir / "tasak.yaml"
        dot_tasak_yaml = current_dir / ".tasak" / "tasak.yaml"

        if dot_tasak_yaml.exists():
            search_paths.append(dot_tasak_yaml)
        
        if tasak_yaml.exists():
            search_paths.append(tasak_yaml)

        if current_dir.parent == current_dir:  # Reached the root
            break
        
        current_dir = current_dir.parent
    
    return list(reversed(search_paths)) # Return in order from root to cwd

def load_and_merge_configs() -> dict:
    """Loads all configs and merges them."""
    merged_config = {}

    # 1. Load global config
    global_config_path = get_global_config_path()
    if global_config_path:
        with open(global_config_path, 'r') as f:
            global_config = yaml.safe_load(f)
            if global_config:
                merged_config.update(global_config)

    # 2. Load and merge local configs
    local_config_paths = find_local_config_paths()
    for path in local_config_paths:
        with open(path, 'r') as f:
            local_config = yaml.safe_load(f)
            if local_config:
                merged_config.update(local_config)

    return merged_config
