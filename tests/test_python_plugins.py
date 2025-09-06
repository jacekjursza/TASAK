import sys
from pathlib import Path

import yaml


def _write_plugin(dir_path: Path, name: str = "myplugin") -> Path:
    plugin_dir = dir_path / ".tasak" / "plugins" / "python"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_path = plugin_dir / f"{name}.py"
    plugin_path.write_text(
        """
DESCRIPTION = "My test plugin"

import argparse


def main():
    parser = argparse.ArgumentParser(prog="myplugin", description="Example plugin")
    parser.add_argument("--name", default="World")
    args = parser.parse_args()
    print(f"Hello {args.name}")


if __name__ == "__main__":
    main()
""".strip()
    )
    return plugin_path


def _write_config(
    path: Path,
    search_path: Path,
    auto_enable_all: bool,
    enabled: list[str] | None = None,
):
    cfg = {
        "apps_config": {"enabled_apps": enabled or []},
        "plugins": {
            "python": {
                "auto_enable_all": auto_enable_all,
                "search_paths": [str(search_path)],
                "python_executable": sys.executable,
            }
        },
    }
    path.write_text(yaml.safe_dump(cfg))


def test_plugin_discovery_and_listing_auto_enable(tmp_path, monkeypatch, capsys):
    from tasak import main as tasak_main

    _write_plugin(tmp_path)
    conf_path = tmp_path / "tasak.yaml"
    search = tmp_path / ".tasak" / "plugins" / "python"
    _write_config(conf_path, search, auto_enable_all=True)

    monkeypatch.setenv("TASAK_CONFIG", str(conf_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["tasak"])  # list apps

    tasak_main.main()
    out = capsys.readouterr().out

    assert "Available applications:" in out
    assert "myplugin" in out
    assert "python-plugin" in out


def test_plugin_exec_via_cli(tmp_path, monkeypatch, capsys):
    from tasak import main as tasak_main

    _write_plugin(tmp_path)
    conf_path = tmp_path / "tasak.yaml"
    search = tmp_path / ".tasak" / "plugins" / "python"
    _write_config(conf_path, search, auto_enable_all=True)

    monkeypatch.setenv("TASAK_CONFIG", str(conf_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["tasak", "myplugin", "--name", "Alice"]
    )  # run plugin

    tasak_main.main()
    out = capsys.readouterr().out
    assert "Hello Alice" in out


def test_plugin_enabled_without_auto_enable(tmp_path, monkeypatch, capsys):
    from tasak import main as tasak_main

    _write_plugin(tmp_path)
    conf_path = tmp_path / "tasak.yaml"
    search = tmp_path / ".tasak" / "plugins" / "python"
    _write_config(conf_path, search, auto_enable_all=False, enabled=["myplugin"])

    monkeypatch.setenv("TASAK_CONFIG", str(conf_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["tasak", "myplugin"]
    )  # run plugin with default name

    tasak_main.main()
    out = capsys.readouterr().out
    assert "Hello World" in out
