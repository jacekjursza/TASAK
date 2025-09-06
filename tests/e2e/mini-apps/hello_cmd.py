#!/usr/bin/env python3
"""Simple command app for testing purposes."""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="Simple test command")
    parser.add_argument("--name", type=str, default="World", help="Name to greet")
    parser.add_argument(
        "--repeat", type=int, default=1, help="Number of times to repeat"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--error", action="store_true", help="Simulate an error")

    args = parser.parse_args()

    if args.error:
        print("Error: Something went wrong!", file=sys.stderr)
        sys.exit(1)

    greeting = f"Hello, {args.name}!"

    if args.json:
        output = {
            "greeting": greeting,
            "count": args.repeat,
            "messages": [greeting for _ in range(args.repeat)],
        }
        print(json.dumps(output, indent=2))
    else:
        for _ in range(args.repeat):
            print(greeting)

    return 0


if __name__ == "__main__":
    sys.exit(main())
