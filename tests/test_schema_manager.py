"""Unit tests for schema_manager module."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import mock_open, patch


from tasak.schema_manager import SchemaManager


class TestSchemaManager:
    """Test SchemaManager class."""

    def test_init_creates_schema_dir(self):
        """Test that initialization creates schema directory."""
        with patch("tasak.schema_manager.Path.mkdir") as mock_mkdir:
            manager = SchemaManager()
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            assert manager.schema_dir == Path.home() / ".tasak" / "schemas"

    @patch("builtins.open", new_callable=mock_open)
    def test_save_schema(self, mock_file):
        """Test saving schema to disk."""
        manager = SchemaManager()
        tools = [
            {
                "name": "tool1",
                "description": "Test tool 1",
                "input_schema": {"type": "object"},
            },
            {
                "name": "tool2",
                "description": "Test tool 2",
                "input_schema": {"type": "string"},
            },
        ]

        schema_file = manager.save_schema("test_app", tools)

        assert schema_file == manager.schema_dir / "test_app.json"
        mock_file.assert_called_once()

        # Check what was written
        handle = mock_file()
        written_data = "".join(call[0][0] for call in handle.write.call_args_list)
        data = json.loads(written_data)

        assert data["app"] == "test_app"
        assert "last_updated" in data
        assert data["version"] == "1.0"
        assert "tool1" in data["tools"]
        assert data["tools"]["tool1"]["description"] == "Test tool 1"
        assert "tool2" in data["tools"]

    @patch("builtins.open", new_callable=mock_open)
    def test_save_schema_with_missing_fields(self, mock_file):
        """Test saving schema with tools missing some fields."""
        manager = SchemaManager()
        tools = [
            {"name": "tool1"},  # Missing description and input_schema
            {"description": "No name tool"},  # Missing name
        ]

        manager.save_schema("test_app", tools)

        handle = mock_file()
        written_data = "".join(call[0][0] for call in handle.write.call_args_list)
        data = json.loads(written_data)

        # Tool with name should be saved
        assert "tool1" in data["tools"]
        assert data["tools"]["tool1"]["description"] == ""
        assert data["tools"]["tool1"]["input_schema"] == {}

        # Tool without name should be skipped
        assert len(data["tools"]) == 1

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"app": "test_app", "tools": {}}',
    )
    @patch("tasak.schema_manager.Path.exists")
    def test_load_schema_exists(self, mock_exists, mock_file):
        """Test loading existing schema."""
        mock_exists.return_value = True
        manager = SchemaManager()

        schema_data = manager.load_schema("test_app")

        assert schema_data is not None
        assert schema_data["app"] == "test_app"
        assert schema_data["tools"] == {}

    @patch("tasak.schema_manager.Path.exists")
    def test_load_schema_not_exists(self, mock_exists):
        """Test loading schema when file doesn't exist."""
        mock_exists.return_value = False
        manager = SchemaManager()

        schema_data = manager.load_schema("test_app")

        assert schema_data is None

    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("tasak.schema_manager.Path.exists")
    def test_load_schema_invalid_json(self, mock_exists, mock_file):
        """Test loading schema with invalid JSON."""
        mock_exists.return_value = True
        manager = SchemaManager()

        schema_data = manager.load_schema("test_app")

        assert schema_data is None

    @patch("builtins.open", new_callable=mock_open)
    @patch("tasak.schema_manager.Path.exists")
    def test_get_schema_age_days(self, mock_exists, mock_file):
        """Test getting schema age in days."""
        mock_exists.return_value = True

        # Create schema data with timestamp from 5 days ago
        past_time = datetime.now() - timedelta(days=5)
        schema_data = {"last_updated": past_time.isoformat()}
        mock_file.return_value.read.return_value = json.dumps(schema_data)

        manager = SchemaManager()
        age = manager.get_schema_age_days("test_app")

        assert age == 5

    @patch("tasak.schema_manager.Path.exists")
    def test_get_schema_age_days_not_exists(self, mock_exists):
        """Test getting schema age when file doesn't exist."""
        mock_exists.return_value = False
        manager = SchemaManager()

        age = manager.get_schema_age_days("test_app")

        assert age is None

    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("tasak.schema_manager.Path.exists")
    def test_get_schema_age_days_no_timestamp(self, mock_exists, mock_file):
        """Test getting schema age when timestamp is missing."""
        mock_exists.return_value = True
        manager = SchemaManager()

        age = manager.get_schema_age_days("test_app")

        assert age is None

    @patch("tasak.schema_manager.Path.exists")
    def test_schema_exists(self, mock_exists):
        """Test checking if schema exists."""
        mock_exists.return_value = True
        manager = SchemaManager()

        exists = manager.schema_exists("test_app")

        assert exists is True
        mock_exists.assert_called_once()

    @patch("tasak.schema_manager.Path.exists")
    def test_schema_not_exists(self, mock_exists):
        """Test checking if schema exists when it doesn't."""
        mock_exists.return_value = False
        manager = SchemaManager()

        exists = manager.schema_exists("test_app")

        assert exists is False

    @patch("tasak.schema_manager.Path.unlink")
    @patch("tasak.schema_manager.Path.exists")
    def test_delete_schema_exists(self, mock_exists, mock_unlink):
        """Test deleting existing schema."""
        mock_exists.return_value = True
        manager = SchemaManager()

        result = manager.delete_schema("test_app")

        assert result is True
        mock_unlink.assert_called_once()

    @patch("tasak.schema_manager.Path.exists")
    def test_delete_schema_not_exists(self, mock_exists):
        """Test deleting non-existent schema."""
        mock_exists.return_value = False
        manager = SchemaManager()

        result = manager.delete_schema("test_app")

        assert result is False

    def test_convert_to_tool_list(self):
        """Test converting schema format back to tool list."""
        manager = SchemaManager()
        schema_data = {
            "tools": {
                "tool1": {
                    "description": "Test tool 1",
                    "input_schema": {"type": "object"},
                },
                "tool2": {
                    "description": "Test tool 2",
                    "input_schema": {"type": "string"},
                },
            }
        }

        tools = manager.convert_to_tool_list(schema_data)

        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"
        assert tools[0]["description"] == "Test tool 1"
        assert tools[0]["input_schema"]["type"] == "object"
        assert tools[1]["name"] == "tool2"

    def test_convert_to_tool_list_empty(self):
        """Test converting empty schema."""
        manager = SchemaManager()
        schema_data = {}

        tools = manager.convert_to_tool_list(schema_data)

        assert tools == []

    def test_convert_to_tool_list_missing_fields(self):
        """Test converting schema with missing fields."""
        manager = SchemaManager()
        schema_data = {
            "tools": {
                "tool1": {},  # Missing description and input_schema
            }
        }

        tools = manager.convert_to_tool_list(schema_data)

        assert len(tools) == 1
        assert tools[0]["name"] == "tool1"
        assert tools[0]["description"] == ""
        assert tools[0]["input_schema"] == {}
