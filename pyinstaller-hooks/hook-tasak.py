# PyInstaller hook for TASAK
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all submodules
hiddenimports = collect_submodules("tasak")

# Add common dependencies that might be missed
hiddenimports += [
    "yaml",
    "mcp",
    "mcp.server",
    "mcp.client",
    "argparse",
    "json",
    "subprocess",
    "pathlib",
    "importlib.metadata",
]

# Collect data files (templates, etc.)
datas = collect_data_files("tasak")
