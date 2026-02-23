"""Entry point for the Ink Density Tool.

Run directly:
    python main.py

Build as a single .exe:
    pyinstaller build.spec
"""
import sys
from gui.app import App


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
