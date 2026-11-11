"""鼠标悬停时的大图预览小窗（用原生 tk，避免 CTk 的 image 兼容问题）"""
import tkinter as tk
from PIL import Image, ImageTk
from theme import COLOR


class PreviewWin(tk.Toplevel):
    MAX = 360

    def __init__(self, master):
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=COLOR["border"])
        self._lbl = tk.Label(self, bd=0, bg=COLOR["panel"])
        self._lbl.pack(padx=2, pady=2)
        self._photo = None
        self._path = None

    def show(self, path: str, x: int, y: int):
        try:
            if path != self._path:
                with Image.open(path) as im:
                    im = im.convert("RGBA")
                    im.thumbnail((self.MAX, self.MAX), Image.LANCZOS)
                    self._photo = ImageTk.PhotoImage(im)
                self._lbl.configure(image=self._photo)
                self._path = path
            self.update_idletasks()
            w, h = self.winfo_reqwidth(), self.winfo_reqheight()
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            x, y = x + 16, y + 16
            if x + w > sw:
                x = max(0, x - w - 32)
            if y + h > sh:
                y = max(0, sh - h - 8)
            self.geometry(f"+{x}+{y}")
            self.deiconify()
            self.lift()
        except Exception:
            self.withdraw()

    def hide(self):
        self.withdraw()
