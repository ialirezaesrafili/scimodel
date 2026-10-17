"""Allow SciModel to run with ``python -m scimodel``."""

from scimodel.interfaces.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
