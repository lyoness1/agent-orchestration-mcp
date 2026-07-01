"""Enables ``python -m maestro`` by delegating to the CLI entry point."""

from maestro.cli import main

# Propagate main()'s return value as the process exit code.
raise SystemExit(main())
