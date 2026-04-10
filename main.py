from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.config import AppConfig
from core.orchestrator import Orchestrator
from gui.main_window import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--background', action='store_true')
    args, _ = parser.parse_known_args()

    app = QApplication(sys.argv)
    app.setApplicationName('Jarvis')
    app.setOrganizationName('AustinUri')
    app.setQuitOnLastWindowClosed(False)

    base_dir = Path(__file__).resolve().parent
    config = AppConfig.load(base_dir / 'config.json')

    orchestrator = Orchestrator(base_dir=base_dir, config=config)
    app.aboutToQuit.connect(orchestrator.shutdown)

    window = MainWindow(orchestrator=orchestrator, config=config, app_dir=base_dir)

    start_hidden = bool(args.background or config.start_minimized)
    if start_hidden:
        if window.tray_icon is not None:
            window.hide()
        else:
            window.showMinimized()
    else:
        window.show()

    exit_code = app.exec()
    config.save(base_dir / 'config.json')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
