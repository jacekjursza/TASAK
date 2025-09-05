"""Schema management for TASAK applications."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class SchemaManager:
    """Manages schemas for MCP applications."""

    def __init__(self):
        self.schema_dir = Path.home() / ".tasak" / "schemas"
        self.schema_dir.mkdir(parents=True, exist_ok=True)

    def save_schema(self, app_name: str, tools: List[Dict[str, Any]]) -> Path:
        """Save tool schema to disk."""
        schema_file = self.schema_dir / f"{app_name}.json"

        schema_data = {
            "app": app_name,
            "last_updated": datetime.now().isoformat(),
            "version": "1.0",
            "tools": {},
        }

        for tool in tools:
            tool_name = tool.get("name")
            if tool_name:
                schema_data["tools"][tool_name] = {
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("input_schema", {}),
                }

        with open(schema_file, "w") as f:
            json.dump(schema_data, f, indent=2)

        return schema_file

    def load_schema(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Load schema from disk if it exists."""
        schema_file = self.schema_dir / f"{app_name}.json"

        if not schema_file.exists():
            return None

        try:
            with open(schema_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def get_schema_age_days(self, app_name: str) -> Optional[int]:
        """Get age of schema in days."""
        schema_file = self.schema_dir / f"{app_name}.json"

        if not schema_file.exists():
            return None

        try:
            with open(schema_file, "r") as f:
                schema_data = json.load(f)
                last_updated = schema_data.get("last_updated")
                if last_updated:
                    update_time = datetime.fromisoformat(last_updated)
                    age = datetime.now() - update_time
                    return age.days
        except Exception:
            pass

        return None

    def schema_exists(self, app_name: str) -> bool:
        """Check if schema exists for an app."""
        schema_file = self.schema_dir / f"{app_name}.json"
        return schema_file.exists()

    def delete_schema(self, app_name: str) -> bool:
        """Delete schema for an app."""
        schema_file = self.schema_dir / f"{app_name}.json"

        if schema_file.exists():
            schema_file.unlink()
            return True

        return False

    def convert_to_tool_list(self, schema_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert schema format back to tool list format."""
        tools = []

        for tool_name, tool_data in schema_data.get("tools", {}).items():
            tools.append(
                {
                    "name": tool_name,
                    "description": tool_data.get("description", ""),
                    "input_schema": tool_data.get("input_schema", {}),
                }
            )

        return tools
