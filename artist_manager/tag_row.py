"""单条目行：缩略图 / 画师串 / 链接 / 权重滑块 / 复制按钮 / 右键菜单"""
import re
import sys
import threading
import tkinter as tk
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import filedialog, messagebox as mb

import customtkinter as ctk
from PIL import Image, ImageOps

from dialogs import EditTagDialog, MoveDialog
from store import IMG_FILTER, open_path
from theme import (THUMB, PAD, RADIUS, CARD_BG, COLOR, SUBTLE, LINK_COLOR,
                   PRIMARY_BTN, SECONDARY, font)

_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="artist-thumb")
_pixel_cache: dict = {}
_pixel_cache_lock = threading.Lock()
_placeholder = None


def placeholder() -> ctk.CTkImage:
    """无图时的灰色占位图（不要给 CTkLabel 设置 image=None，会触发 Tk 报错）"""
    global _placeholder
    if _placeholder is None:
        _placeholder = ctk.CTkImage(Image.new("RGB", (THUMB * 2, THUMB * 2), (58, 58, 62)),
                                    size=(THUMB, THUMB))
    return _placeholder


def load_thumb_pixels(path: Path):
    try:
        key = (str(path), path.stat().st_mtime_ns)
        with _pixel_cache_lock:
            cached = _pixel_cache.get(key)
        if cached is not None:
            return cached.copy()
        with Image.open(path) as im:
            im.draft("RGB", (THUMB * 4, THUMB * 4))      # JPEG 快速降采样
            im = ImageOps.exif_transpose(im).convert("RGB")
            im = ImageOps.fit(im, (THUMB * 2, THUMB * 2), Image.LANCZOS)  # 居中裁成方形
        with _pixel_cache_lock:
            if len(_pixel_cache) > 300:
                _pixel_cache.clear()
            _pixel_cache[key] = im.copy()
        return im
    except Exception:
        return None


class TagRow(ctk.CTkFrame):
    def __init__(self, master, app, group: str, tag: dict):
        super().__init__(master, corner_radius=RADIUS, fg_color=CARD_BG,
                         border_width=1, border_color=COLOR["border"])
        self.app, self.store = app, app.store
        self.group, self.tag = group, tag
        self._wl = 0
        self._thumb_generation = 0
        self._thumb_future = None
        self.grid_columnconfigure(1, weight=1)

        # 缩略图：悬停预览，点击打开文件夹（没有图则导入）
        self.thumb = ctk.CTkLabel(self, text="", width=THUMB, height=THUMB,
                                  image=placeholder(), compound="center",
                                  text_color=SUBTLE, font=font(11), cursor="hand2")
        self.thumb.grid(row=0, column=0, rowspan=3, padx=(PAD, 6), pady=PAD, sticky="n")
        self.thumb.bind("<Enter>", lambda e: self._hover())
        self.thumb.bind("<Leave>", lambda e: self.app.preview.hide())
        self.thumb.bind("<Button-1>", lambda e: self._thumb_click())
        self.app.register_drop_target(self.thumb, self._on_drop)

        # 画师串（自动换行）
        identity = ctk.CTkFrame(self, fg_color="transparent")
        identity.grid(row=0, column=1, sticky="ew", padx=(4, 6), pady=(PAD, 0))
        display_name = tag.get("display_name", "").strip() or tag["text"].strip()
        if len(display_name) > 64:
            display_name = display_name[:61].rstrip() + "…"
        self.name = ctk.CTkLabel(identity, text=display_name, anchor="w", justify="left",
                                 wraplength=320, font=font(13, True), text_color=COLOR["text"])
        self.name.pack(side="left", anchor="w")
        self.name.bind("<Button-1>", lambda e: self.copy())
        for label in tag.get("labels", [])[:4]:
            ctk.CTkLabel(identity, text=label, font=font(9, True),
                         text_color=COLOR["accent"], fg_color=COLOR["accent_soft"],
                         corner_radius=7, padx=7, pady=3).pack(side="left", padx=(7, 0))

        # A short explanation stays secondary to the display name.
        note = tag.get("note", "").strip()
        self.lbl_meta = ctk.CTkLabel(self, text=note, anchor="w", font=font(10),
                                     text_color=SUBTLE)
        if note:
            self.lbl_meta.grid(row=1, column=1, sticky="ew", padx=(4, 6))

        # Link (when present)
        self.lbl_link = ctk.CTkLabel(self, text="", anchor="w", font=font(11),
                                     text_color=LINK_COLOR, cursor="hand2")
        self.lbl_link.grid(row=2, column=1, sticky="ew", padx=(4, 6))
        self.lbl_link.bind("<Button-1>", lambda e: self.open_link())

        # 操作按钮
        af = ctk.CTkFrame(self, fg_color="transparent")
        af.grid(row=0, column=2, rowspan=3, padx=(0, PAD), pady=PAD, sticky="e")
        ctk.CTkButton(af, text="＋ 组合", width=76, height=30, command=self.add_to_combo,
                      **PRIMARY_BTN).pack(pady=(0, 6))
        self.btn_more = ctk.CTkButton(af, text="更多  ···", width=76, height=30,
                                      command=lambda: self._popup(widget=self.btn_more),
                                      **SECONDARY)
        self.btn_more.pack()

        # 右键菜单
        for w in (self, self.thumb, self.name, self.lbl_link):
            w.bind("<Button-3>", self._popup)
            if sys.platform == "darwin":
                w.bind("<Button-2>", self._popup)

        self.bind("<Configure>", self._on_resize)
        self.app.register_drop_target(self, self._on_drop)
        self.app.register_drop_target(self.name, self._on_drop)
        self._refresh_link()
        self.refresh_thumb()

    # ---------------- 显示 ----------------
    def _on_resize(self, e):
        scale = getattr(self, "_get_widget_scaling", lambda: 1)()
        wl = int(max(88, e.width - THUMB - 76 - 3 * PAD - 16) / scale)
        if abs(wl - self._wl) > 12:     # 防抖，避免换行高度变化引起的循环
            self._wl = wl
            self.name.configure(wraplength=wl)

    def _refresh_link(self):
        link = self.tag.get("link", "")
        if link:
            short = re.sub(r"^https?://(www\.)?", "", link)
            self.lbl_link.configure(text="↗ " + (short if len(short) <= 60 else short[:60] + "…"))
            self.lbl_link.grid()
        else:
            self.lbl_link.grid_remove()

    def refresh_thumb(self):
        self._thumb_generation += 1
        generation = self._thumb_generation
        self.thumb.configure(image=placeholder(), text="···")
        future = _executor.submit(self._load_thumb_pixels)
        self._thumb_future = future

        def finish(done):
            try:
                pixels = done.result()
            except Exception:
                pixels = None
            try:
                self.after(0, lambda: self._apply_thumb(pixels, generation))
            except tk.TclError:
                pass

        future.add_done_callback(finish)

    def destroy(self):
        future = self._thumb_future
        if future is not None:
            future.cancel()
        super().destroy()

    def _load_thumb_pixels(self):
        image_path = self.store.first_image(self.tag)
        return load_thumb_pixels(image_path) if image_path else None

    def _apply_thumb(self, pixels, generation):
        if generation != self._thumb_generation or not self.winfo_exists():
            return
        if pixels is None:
            self.thumb.configure(image=placeholder(), text="拖入图片" if self.app._dnd_enabled else "无图")
            return
        self.thumb.configure(image=ctk.CTkImage(pixels, size=(THUMB, THUMB)), text="")

    def _hover(self):
        p = self.store.first_image(self.tag)
        if p:
            self.app.preview.show(str(p), self.winfo_rootx() + THUMB + PAD, self.winfo_rooty())

    def _thumb_click(self):
        if self.store.first_image(self.tag):
            self.open_folder()
        else:
            self.import_images()

    def _on_drop(self, event):
        try:
            paths = self.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        paths = [p for p in paths if Path(p).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}]
        if paths:
            self.import_images(paths)
        return "copy"

    # ---------------- 动作 ----------------
    def copy(self):
        self.app.copy_text(self.store.format_tag(self.group, self.tag))

    def open_link(self):
        link = self.tag.get("link", "").strip()
        if not link:
            return
        if not link.startswith(("http://", "https://")):
            link = "https://" + link
        webbrowser.open(link)

    def edit(self):
        res = EditTagDialog(
            self.app, "编辑记录", self.tag["text"], self.tag.get("link", ""),
            self.tag.get("weight", 1.0), self.tag.get("display_name", ""),
            self.tag.get("labels", []), self.tag.get("note", "")).run()
        if res:
            (self.tag["text"], self.tag["link"], self.tag["weight"],
             self.tag["display_name"], self.tag["labels"], self.tag["note"]) = res[:6]
            mode = self.store.groups[self.group].get("sort_mode", "manual")
            self.store.set_sort_mode(self.group, mode)
            if res[6]:
                self.store.import_images(self.group, self.tag, res[6])
            self.app.refresh_groups()
            if res[6]:
                self.app.toast(f"已导入 {len(res[6])} 张图片")

    def import_images(self, files=None):
        if files is None:
            files = filedialog.askopenfilenames(parent=self.app, title="选择预览图（可多选）",
                                                filetypes=IMG_FILTER)
        if files:
            n = self.store.import_images(self.group, self.tag, files)
            self.refresh_thumb()
            self.app.toast(f"已导入 {n} 张图片")

    def add_to_combo(self):
        self.app.combo.add_item(self.group, self.tag)

    def open_folder(self):
        rel = self.tag.get("folder", "")
        if rel and (self.store.root_dir / rel).is_dir():
            open_path(self.store.root_dir / rel)
        else:
            self.app.toast("还没有图片文件夹，请先导入图片")

    def clear_images(self):
        if not self.tag.get("folder"):
            return
        if mb.askyesno("确认", "删除该条目的图片文件夹及其中所有图片？", parent=self.app):
            self.store.remove_item_folder(self.tag)
            self.refresh_thumb()

    def move(self, copy=False):
        names = list(self.store.groups.keys())
        if len(names) <= 1:
            return self.app.toast("只有一个分组，无法移动")
        target = MoveDialog(self.app, names, self.group).run()
        if target:
            if copy:
                self.store.copy_tag(self.group, target, self.tag)
            else:
                self.store.move_tag(self.group, target, self.tag)
            self.app.refresh_groups()

    def delete(self):
        if self.tag.get("folder") and not mb.askyesno(
                "确认", "该条目有图片文件夹，删除条目会一并删除图片，继续？", parent=self.app):
            return
        self.store.delete_tag(self.group, self.tag)
        self.app.refresh_groups()

    # ---------------- 菜单 ----------------
    def _popup(self, event=None, widget=None):
        self.app.preview.hide()
        m = tk.Menu(self, tearoff=0, bg=COLOR["panel_alt"], fg=COLOR["text"],
                    activebackground=COLOR["accent"], activeforeground=COLOR["app"],
                    disabledforeground=COLOR["muted"], borderwidth=0,
                    relief="flat", font=font(10))
        m.add_command(label="编辑", command=self.edit)
        m.add_command(label="打开图片文件夹", command=self.open_folder)
        m.add_command(label="复制到其他分组…", command=lambda: self.move(copy=True))
        m.add_command(label="移动到其他分组…", command=self.move)
        m.add_command(label="删除", command=self.delete)
        if event is not None:
            x, y = event.x_root, event.y_root
        else:
            x, y = widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height()
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()
