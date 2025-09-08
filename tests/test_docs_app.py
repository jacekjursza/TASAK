from pathlib import Path
from unittest.mock import patch

from tasak.docs_app import run_docs_app


def _make_fs(tmp_path: Path):
    # root
    (tmp_path / "readme.md").write_text("# Readme\nroot file\n", encoding="utf-8")
    (tmp_path / "changelog.md").write_text("Changelog\n", encoding="utf-8")
    # subdir guides
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "intro.md").write_text("Intro\n", encoding="utf-8")
    deep = guides / "deep"
    deep.mkdir()
    (deep / "nested.md").write_text("Nested\n", encoding="utf-8")
    # include dir
    agent = tmp_path / ".agent"
    agent.mkdir()
    # Create file WITHOUT trailing newline to test newline append
    (agent / "AGENTS.md").write_text("Agents header", encoding="utf-8")


def _app_config(tmp_path: Path):
    return {"type": "docs", "meta": {"directory": str(tmp_path)}}


def test_docs_list_root(tmp_path, capsys):
    _make_fs(tmp_path)
    cfg = _app_config(tmp_path)
    run_docs_app("docsapp", cfg, [])
    out = capsys.readouterr().out
    assert '"docsapp" commands:' in out
    assert "readme" in out and "changelog" in out
    assert '"docsapp" sub-apps:' in out and "guides" in out


def test_docs_navigate_and_list(tmp_path, capsys):
    _make_fs(tmp_path)
    cfg = _app_config(tmp_path)
    run_docs_app("docsapp", cfg, ["guides"])
    out = capsys.readouterr().out
    assert '"docsapp" commands:' in out and "intro" in out
    assert '"docsapp" sub-apps:' in out and "deep" in out


def test_docs_view_file_without_ext(tmp_path, capsys):
    _make_fs(tmp_path)
    cfg = _app_config(tmp_path)
    run_docs_app("docsapp", cfg, ["guides", "intro"])
    out = capsys.readouterr().out
    assert "Intro" in out


def test_docs_view_file_with_ext(tmp_path, capsys):
    _make_fs(tmp_path)
    cfg = _app_config(tmp_path)
    run_docs_app("docsapp", cfg, ["guides", "deep", "nested.md"])
    out = capsys.readouterr().out
    assert "Nested" in out


def test_docs_not_found_lists_parent(tmp_path, capsys):
    _make_fs(tmp_path)
    cfg = _app_config(tmp_path)
    with patch("sys.exit") as mock_exit:
        run_docs_app("docsapp", cfg, ["guides", "missing"])
        mock_exit.assert_called()
    out = capsys.readouterr().out
    # Should list the parent directory (guides)
    assert '"docsapp" commands:' in out and "intro" in out


def test_docs_include_expansion_default_enabled(tmp_path, capsys):
    _make_fs(tmp_path)
    # Create a file that includes another
    (tmp_path / "with_include.md").write_text(
        "Before\n@.agent/AGENTS.md\nAfter", encoding="utf-8"
    )
    cfg = _app_config(tmp_path)
    run_docs_app("docsapp", cfg, ["with_include"])
    out = capsys.readouterr().out
    # Included content appears and output ends with a newline
    assert "Before" in out
    assert "Agents header" in out
    assert "After" in out
    assert out.endswith("\n")


def test_docs_include_disabled_via_config(tmp_path, capsys):
    _make_fs(tmp_path)
    (tmp_path / "with_include.md").write_text(
        "Start\n@.agent/AGENTS.md\nEnd", encoding="utf-8"
    )
    cfg = _app_config(tmp_path)
    cfg["meta"]["respect_include"] = False
    run_docs_app("docsapp", cfg, ["with_include"])
    out = capsys.readouterr().out
    # Literal include string remains
    assert "@.agent/AGENTS.md" in out


def test_docs_exclude_patterns_listing_and_include(tmp_path, capsys):
    _make_fs(tmp_path)
    # Add .git dir and extra file
    (tmp_path / ".git").mkdir()
    (tmp_path / "secret.md").write_text("Top secret\n", encoding="utf-8")
    # Create a file that tries to include an excluded file
    (tmp_path / "tryinc.md").write_text("X\n@secret.md\nY", encoding="utf-8")

    cfg = _app_config(tmp_path)
    # Exclude .git directory, a subtree, and a specific file
    cfg["meta"]["exclude"] = [
        ".git/**",
        "guides/deep/**",
        "secret.md",
    ]

    # Root listing should not include .git or secret
    run_docs_app("docsapp", cfg, [])
    out = capsys.readouterr().out
    assert ".git" not in out
    assert "secret" not in out
    # Guides listing should not show deep
    run_docs_app("docsapp", cfg, ["guides"])
    out2 = capsys.readouterr().out
    assert "deep" not in out2

    # Including an excluded file should not expand; literal line remains
    run_docs_app("docsapp", cfg, ["tryinc"])  # prints doc
    out3 = capsys.readouterr().out
    assert "@secret.md" in out3


def test_docs_flatten_only_dirs(tmp_path, capsys):
    # Build structure:
    # only/x/y/file.md        -> should show as 'only:x:y'
    # folder/mid/subsub/f.md  -> should show as 'folder:mid:subsub'
    # mixed has md at its level -> 'mixed'
    (tmp_path / "only" / "x" / "y").mkdir(parents=True)
    (tmp_path / "only" / "x" / "y" / "file.md").write_text("hello\n", encoding="utf-8")
    (tmp_path / "folder" / "mid" / "subsub").mkdir(parents=True)
    (tmp_path / "folder" / "mid" / "subsub" / "f.md").write_text(
        "world\n", encoding="utf-8"
    )
    (tmp_path / "mixed").mkdir()
    (tmp_path / "mixed" / "r.md").write_text("readme\n", encoding="utf-8")

    cfg = _app_config(tmp_path)
    run_docs_app("docsapp", cfg, [])
    out = capsys.readouterr().out
    # Sub-apps line should contain flattened names
    assert '"docsapp" sub-apps:' in out
    # flattened entries
    assert "only:x:y" in out
    assert "folder:mid:subsub" in out
    # 'mixed' shouldn't be flattened because it has md at its own level
    assert "mixed" in out


def test_docs_colon_navigation(tmp_path, capsys):
    # Build deeper structure and test colon-separated args
    (tmp_path / "A" / "B" / "C").mkdir(parents=True)
    (tmp_path / "A" / "B" / "C" / "doc.md").write_text("content\n", encoding="utf-8")

    cfg = _app_config(tmp_path)
    # Navigate to A/B using colon shorthand
    run_docs_app("docsapp", cfg, ["A:B"])
    out = capsys.readouterr().out
    assert '"docsapp" at /A/B' in out
    assert '"docsapp" sub-apps:' in out and "C" in out

    # View document using colon shorthand and explicit doc name without .md
    run_docs_app("docsapp", cfg, ["A:B:C", "doc"])
    out2 = capsys.readouterr().out
    assert out2.strip().startswith("content")
