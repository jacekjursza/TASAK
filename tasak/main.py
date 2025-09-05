import argparse

def main():
    """Main entry point for the TASAK application."""
    parser = argparse.ArgumentParser(
        prog="tasak",
        description="TASAK: The Agent's Swiss Army Knife. A command-line proxy for AI agents."
    )

    parser.add_argument(
        "app_name",
        nargs='?',
        help="The name of the application to run."
    )

    args, unknown = parser.parse_known_args()

    if args.app_name:
        print(f"Running app: {args.app_name}")
        # Here we will later dispatch to the correct app runner
        # For now, just print the app name and any unknown arguments
        if unknown:
            print(f"With arguments: {unknown}")
    else:
        # If no app name is provided, print the help message.
        parser.print_help()

if __name__ == "__main__":
    main()
