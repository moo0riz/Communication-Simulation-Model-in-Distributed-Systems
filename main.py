from __future__ import annotations

from tkinter import ttk

from app_tk import DistributedCommsSimulator


def main() -> None:
    app = DistributedCommsSimulator()

    try:
        style = ttk.Style(app)
        for theme in ("aqua", "clam", "alt", "default"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break
    except Exception:
        pass

    app.mainloop()


if __name__ == "__main__":
    main()
