from __future__ import annotations

import sys


def main() -> int:
    if "--legacy" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--legacy"]
        from legacy_main import main as legacy_main
        return legacy_main()
    from workspace.launcher import main as workspace_main
    return workspace_main()


if __name__ == "__main__":
    raise SystemExit(main())
