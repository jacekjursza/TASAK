"""Use official mcp-remote for Atlassian authentication."""

import subprocess
import sys


def authenticate_with_mcp_remote():
    """
    Use the official mcp-remote tool for Atlassian OAuth.
    This is the recommended approach by Atlassian.
    """
    print("Using official mcp-remote for authentication...")
    print("This will install and run the Atlassian MCP proxy temporarily.")

    # Run mcp-remote with npx (auto-installs if needed)
    cmd = [
        "npx",
        "-y",
        "mcp-remote",
        "https://mcp.atlassian.com/v1/sse",
        "--auth-only",  # Just authenticate, don't start full proxy
    ]

    try:
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutes timeout
        )

        if result.returncode == 0:
            print("Authentication successful via mcp-remote!")
            # Parse any token info from output if available
            return True
        else:
            print(f"Authentication failed: {result.stderr}", file=sys.stderr)
            return False

    except subprocess.TimeoutExpired:
        print("Authentication timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("npx not found. Please install Node.js first.", file=sys.stderr)
        print("Visit: https://nodejs.org/", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error running mcp-remote: {e}", file=sys.stderr)
        return False


def main():
    """Main function for command line execution."""
    success = authenticate_with_mcp_remote()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
