import pytest
import yaml
from unittest.mock import patch

from tasak.config import (
    get_global_config_path,
    find_local_config_paths,
    load_and_merge_configs,
)


class TestGetGlobalConfigPath:
    """Tests for get_global_config_path function."""

    def test_global_config_exists(self, tmp_path):
        """Test when global config exists."""
        # Create mock home directory
        mock_home = tmp_path / "home"
        mock_home.mkdir()

        # Create .tasak/tasak.yaml
        tasak_dir = mock_home / ".tasak"
        tasak_dir.mkdir()
        config_file = tasak_dir / "tasak.yaml"
        config_file.write_text("test: config")

        with patch("pathlib.Path.home", return_value=mock_home):
            result = get_global_config_path()
            assert result == config_file
            assert result.exists()

    def test_global_config_not_exists(self, tmp_path):
        """Test when global config doesn't exist."""
        mock_home = tmp_path / "home"
        mock_home.mkdir()

        with patch("pathlib.Path.home", return_value=mock_home):
            result = get_global_config_path()
            assert result is None


class TestFindLocalConfigPaths:
    """Tests for find_local_config_paths function."""

    def test_no_local_configs(self, tmp_path):
        """Test when no local configs exist."""
        work_dir = tmp_path / "project" / "subdir"
        work_dir.mkdir(parents=True)

        with patch("pathlib.Path.cwd", return_value=work_dir):
            result = find_local_config_paths()
            assert result == []

    def test_single_tasak_yaml(self, tmp_path):
        """Test with single tasak.yaml in current directory."""
        work_dir = tmp_path / "project"
        work_dir.mkdir()
        config_file = work_dir / "tasak.yaml"
        config_file.write_text("test: config")

        with patch("pathlib.Path.cwd", return_value=work_dir):
            result = find_local_config_paths()
            assert len(result) == 1
            assert result[0] == config_file

    def test_single_dot_tasak_yaml(self, tmp_path):
        """Test with .tasak/tasak.yaml in current directory."""
        work_dir = tmp_path / "project"
        work_dir.mkdir()
        dot_tasak = work_dir / ".tasak"
        dot_tasak.mkdir()
        config_file = dot_tasak / "tasak.yaml"
        config_file.write_text("test: config")

        with patch("pathlib.Path.cwd", return_value=work_dir):
            result = find_local_config_paths()
            assert len(result) == 1
            assert result[0] == config_file

    def test_both_configs_in_same_dir(self, tmp_path):
        """Test when both tasak.yaml and .tasak/tasak.yaml exist."""
        work_dir = tmp_path / "project"
        work_dir.mkdir()

        # Create both configs
        config1 = work_dir / "tasak.yaml"
        config1.write_text("test: config1")

        dot_tasak = work_dir / ".tasak"
        dot_tasak.mkdir()
        config2 = dot_tasak / "tasak.yaml"
        config2.write_text("test: config2")

        with patch("pathlib.Path.cwd", return_value=work_dir):
            result = find_local_config_paths()
            assert len(result) == 2
            # Order: tasak.yaml comes before .tasak/tasak.yaml
            # because .tasak is checked first and list is reversed
            assert result[0] == config1
            assert result[1] == config2

    def test_hierarchical_configs(self, tmp_path):
        """Test finding configs in parent directories."""
        # Create directory structure
        root = tmp_path / "root"
        project = root / "project"
        subdir = project / "subdir"
        subdir.mkdir(parents=True)

        # Create configs at different levels
        root_config = root / "tasak.yaml"
        root_config.write_text("level: root")

        project_config = project / "tasak.yaml"
        project_config.write_text("level: project")

        with patch("pathlib.Path.cwd", return_value=subdir):
            result = find_local_config_paths()
            assert len(result) == 2
            # Should be in order from root to cwd
            assert result[0] == root_config
            assert result[1] == project_config


class TestLoadAndMergeConfigs:
    """Tests for load_and_merge_configs function."""

    def test_empty_configs(self, tmp_path):
        """Test when no configs exist."""
        work_dir = tmp_path / "project"
        work_dir.mkdir()
        mock_home = tmp_path / "home"
        mock_home.mkdir()

        with patch("pathlib.Path.cwd", return_value=work_dir):
            with patch("pathlib.Path.home", return_value=mock_home):
                result = load_and_merge_configs()
                assert result == {}

    def test_isolate_in_mid_level_stops_bubbling(self, tmp_path):
        """apps_config.isolate at a mid-level local config ignores parents and global."""
        # Structure: /root -> /root/project -> /root/project/subdir (cwd)
        root = tmp_path / "root"
        project = root / "project"
        subdir = project / "subdir"
        subdir.mkdir(parents=True)

        mock_home = tmp_path / "home"
        mock_home.mkdir()

        # Global config
        gfile = mock_home / ".tasak" / "tasak.yaml"
        gfile.parent.mkdir(parents=True)
        gfile.write_text(yaml.dump({"header": "Global", "from_global": True}))

        # Root config (would normally apply)
        (root / "tasak.yaml").write_text(
            yaml.dump({"header": "Root", "from_root": True})
        )

        # Project config with isolate
        (project / "tasak.yaml").write_text(
            yaml.dump(
                {
                    "header": "Project",
                    "apps_config": {"isolate": True},
                    "from_project": True,
                }
            )
        )

        # Deeper config in subdir
        (subdir / "tasak.yaml").write_text(yaml.dump({"from_subdir": True}))

        with patch("pathlib.Path.cwd", return_value=subdir):
            with patch("pathlib.Path.home", return_value=mock_home):
                result = load_and_merge_configs()

        # Isolation should cause merge to start at project level (ignore global and root)
        assert result["header"] == "Project"
        assert result.get("from_global") is None
        assert result.get("from_root") is None
        # But subdir should still merge on top
        assert result.get("from_project") is True
        assert result.get("from_subdir") is True

    def test_isolate_in_cwd_ignores_all_ancestors(self, tmp_path):
        """apps_config.isolate in current dir ignores all parents and global."""
        work = tmp_path / "work"
        parent = work / "parent"
        cwd = parent / "here"
        cwd.mkdir(parents=True)

        mock_home = tmp_path / "home"
        (mock_home / ".tasak").mkdir(parents=True)
        (mock_home / ".tasak" / "tasak.yaml").write_text(
            yaml.dump({"from_global": True})
        )

        (work / "tasak.yaml").write_text(yaml.dump({"from_work": True}))
        (parent / "tasak.yaml").write_text(yaml.dump({"from_parent": True}))
        (cwd / "tasak.yaml").write_text(
            yaml.dump({"apps_config": {"isolate": True}, "from_cwd": True})
        )

        with patch("pathlib.Path.cwd", return_value=cwd):
            with patch("pathlib.Path.home", return_value=mock_home):
                result = load_and_merge_configs()

        assert result == {"apps_config": {"isolate": True}, "from_cwd": True}

    def test_global_config_only(self, tmp_path):
        """Test with only global config."""
        work_dir = tmp_path / "project"
        work_dir.mkdir()
        mock_home = tmp_path / "home"
        mock_home.mkdir()

        # Create global config
        tasak_dir = mock_home / ".tasak"
        tasak_dir.mkdir()
        config_file = tasak_dir / "tasak.yaml"
        config_data = {
            "header": "Global Config",
            "apps_config": {"enabled_apps": ["app1", "app2"]},
            "app1": {"name": "App One"},
        }
        config_file.write_text(yaml.dump(config_data))

        with patch("pathlib.Path.cwd", return_value=work_dir):
            with patch("pathlib.Path.home", return_value=mock_home):
                result = load_and_merge_configs()
                assert result == config_data

    def test_local_overrides_global(self, tmp_path):
        """Test that local config overrides global config."""
        work_dir = tmp_path / "project"
        work_dir.mkdir()
        mock_home = tmp_path / "home"
        mock_home.mkdir()

        # Create global config
        tasak_dir = mock_home / ".tasak"
        tasak_dir.mkdir()
        global_config_file = tasak_dir / "tasak.yaml"
        global_config = {
            "header": "Global Config",
            "app1": {"name": "Global App", "version": "1.0"},
            "app2": {"name": "App Two"},
        }
        global_config_file.write_text(yaml.dump(global_config))

        # Create local config
        local_config_file = work_dir / "tasak.yaml"
        local_config = {
            "header": "Local Config",
            "app1": {"name": "Local App", "extra": "field"},
            "app3": {"name": "App Three"},
        }
        local_config_file.write_text(yaml.dump(local_config))

        with patch("pathlib.Path.cwd", return_value=work_dir):
            with patch("pathlib.Path.home", return_value=mock_home):
                result = load_and_merge_configs()

                # Local header should override
                assert result["header"] == "Local Config"

                # Local app1 should completely override global app1
                assert result["app1"] == {"name": "Local App", "extra": "field"}

                # app2 from global should remain
                assert result["app2"] == {"name": "App Two"}

                # app3 from local should be added
                assert result["app3"] == {"name": "App Three"}

    def test_multiple_local_configs_merge(self, tmp_path):
        """Test merging multiple local configs in hierarchy."""
        # Create directory structure
        root = tmp_path / "root"
        project = root / "project"
        subdir = project / "subdir"
        subdir.mkdir(parents=True)

        mock_home = tmp_path / "home"
        mock_home.mkdir()

        # Root level config
        root_config_file = root / "tasak.yaml"
        root_config = {
            "header": "Root Config",
            "app1": {"level": "root"},
            "app2": {"level": "root"},
        }
        root_config_file.write_text(yaml.dump(root_config))

        # Project level config
        project_config_file = project / "tasak.yaml"
        project_config = {
            "header": "Project Config",
            "app2": {"level": "project"},
            "app3": {"level": "project"},
        }
        project_config_file.write_text(yaml.dump(project_config))

        with patch("pathlib.Path.cwd", return_value=subdir):
            with patch("pathlib.Path.home", return_value=mock_home):
                result = load_and_merge_configs()

                # Project header should win
                assert result["header"] == "Project Config"

                # app1 from root should remain
                assert result["app1"] == {"level": "root"}

                # app2 from project should override root
                assert result["app2"] == {"level": "project"}

                # app3 from project should be added
                assert result["app3"] == {"level": "project"}

    def test_invalid_yaml_handling(self, tmp_path):
        """Test handling of invalid YAML files."""
        work_dir = tmp_path / "project"
        work_dir.mkdir()
        mock_home = tmp_path / "home"
        mock_home.mkdir()

        # Create invalid YAML
        config_file = work_dir / "tasak.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with patch("pathlib.Path.cwd", return_value=work_dir):
            with patch("pathlib.Path.home", return_value=mock_home):
                with pytest.raises(yaml.YAMLError):
                    load_and_merge_configs()

    def test_empty_yaml_file(self, tmp_path):
        """Test handling of empty YAML files."""
        work_dir = tmp_path / "project"
        work_dir.mkdir()
        mock_home = tmp_path / "home"
        mock_home.mkdir()

        # Create empty YAML
        config_file = work_dir / "tasak.yaml"
        config_file.write_text("")

        with patch("pathlib.Path.cwd", return_value=work_dir):
            with patch("pathlib.Path.home", return_value=mock_home):
                result = load_and_merge_configs()
                assert result == {}
