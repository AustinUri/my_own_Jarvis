from __future__ import annotations

import sys


def main() -> int:
    if "--private-ai" in sys.argv:
        from pathlib import Path
        from PySide6.QtWidgets import QApplication
        from agent.private_brain import PrivateBrain
        from core.config import AppConfig
        from workspace.private_ai_dialog import open_private_ai

        app = QApplication([sys.argv[0]])
        config = AppConfig.load(Path(__file__).resolve().with_name("config.json"))
        dialog = open_private_ai(lambda: PrivateBrain(config=config))
        if dialog is None:
            return 1
        return app.exec()
    if "--legacy" in sys.argv:
        sys.argv = [arg for arg in sys.argv if arg != "--legacy"]
        from legacy_main import main as legacy_main
        return legacy_main()
    from workspace.launcher import main as workspace_main
    return workspace_main()


if __name__ == "__main__":
    raise SystemExit(main())
