"""弹窗组件：GroupDialog / EditTagDialog / BatchDialog / MoveDialog。
用法：result = XxxDialog(master, ...).run()    取消时返回 None
"""
from tkinter import filedialog, messagebox as mb
import customtkinter as ctk
from theme import (APP_BG, CARD_BG, COLOR, ENTRY_STYLE, PRIMARY_BTN, RADIUS,
                   font, SECONDARY, SUBTLE)


class BaseDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, w: int, h: int):
        super().__init__(master)
        self.configure(fg_color=APP_BG)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        self.transient(master)
        master.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + (master.winfo_height() - h) // 3
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(150, self._grab)   # 窗口还不可见时 grab_set 会失败，所以稍等

    def _grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _buttons(self, ok_text: str = "确定"):
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(side="bottom", fill="x", padx=20, pady=(8, 16))
        ctk.CTkButton(bf, text="取消", width=90, height=36, command=self.destroy,
                      **SECONDARY).pack(side="right")
        ctk.CTkButton(bf, text=ok_text, width=90, height=36, command=self._ok,
                      **PRIMARY_BTN).pack(side="right", padx=(0, 8))

    def _label(self, text: str):
        ctk.CTkLabel(self, text=text, anchor="w", font=font(12), text_color=COLOR["text_soft"]
                     ).pack(fill="x", padx=20, pady=(12, 2))

    def _entry(self, label: str, value: str = "", placeholder: str = "") -> ctk.CTkEntry:
        self._label(label)
        e = ctk.CTkEntry(self, placeholder_text=placeholder, height=38, **ENTRY_STYLE)
        e.pack(fill="x", padx=20)
        if value:
            e.insert(0, value)
        return e

    def _warn(self, msg: str):
        mb.showwarning("提示", msg, parent=self)

    def _ok(self):
        raise NotImplementedError

    def run(self):
        self.wait_window()
        return self.result


class GroupDialog(BaseDialog):
    def __init__(self, master, name="", prefix="", suffix=""):
        super().__init__(master, "分组设置", 440, 380)
        self._buttons()
        self.e_name = self._entry("分组名称", name, "例如：常用画师")
        self.e_pre = self._entry("固定前缀（拼在权重之后）", prefix, "例如：::")
        self.e_suf = self._entry("固定后缀", suffix, "例如：::")
        self.lbl_demo = ctk.CTkLabel(self, text="", anchor="w", justify="left",
                                     wraplength=390, font=font(12), text_color=COLOR["accent"])
        self.lbl_demo.pack(fill="x", padx=20, pady=(14, 0))
        for e in (self.e_pre, self.e_suf):
            e.bind("<KeyRelease>", lambda ev: self._demo())
        self.bind("<Return>", lambda e: self._ok())
        self._demo()
        self.after(250, self.e_name.focus_set)

    def _demo(self):
        self.lbl_demo.configure(
            text=f"输出示例：1.0{self.e_pre.get()}画师串{self.e_suf.get()}")

    def _ok(self):
        name = self.e_name.get().strip()
        if not name:
            return self._warn("分组名称不能为空")
        self.result = (name, self.e_pre.get(), self.e_suf.get())
        self.destroy()


class FormSection(ctk.CTkFrame):
    """Reusable labeled section used by structured editing dialogs."""

    def __init__(self, master, title: str):
        super().__init__(master, corner_radius=RADIUS, fg_color=CARD_BG,
                         border_width=1, border_color=COLOR["border"])
        ctk.CTkLabel(self, text=title, anchor="w", font=font(12, True)
                     ).pack(fill="x", padx=12, pady=(9, 6))


class EditTagDialog(BaseDialog):
    """新增 / 编辑提示词记录。"""

    def __init__(self, master, title="编辑条目", text="", link="", weight=1.0,
                 display_name="", labels=None, note=""):
        super().__init__(master, title, 560, 760)
        self._buttons()
        self.selected_images = []
        self.e_display = self._entry("显示名称（可选）", display_name, "例如：柔和水彩角色")
        self.e_labels = self._entry("组内标签（逗号分隔）", ", ".join(labels or []),
                                    "例如：水彩，柔和，角色 A")
        self.e_note = self._entry("说明（可选）", note, "补充风格、适用场景或使用提醒")
        image_row = ctk.CTkFrame(self, fg_color="transparent")
        image_row.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkButton(image_row, text="选择参考图片…", height=34,
                      command=self._choose_images, **SECONDARY).pack(side="left")
        self.lbl_images = ctk.CTkLabel(image_row, text="未选择图片", text_color=SUBTLE,
                                       font=font(11))
        self.lbl_images.pack(side="left", padx=10)
        self.section_text = FormSection(self, "画师串")
        self.section_text.pack(fill="both", expand=True, padx=20, pady=(10, 6))
        self.tb = ctk.CTkTextbox(self, height=120, wrap="word", font=font(13),
                                 fg_color=COLOR["input"], text_color=COLOR["text"],
                                 border_color=COLOR["border"], corner_radius=8)
        self.tb.pack(in_=self.section_text, fill="both", expand=True, padx=10, pady=(0, 10))
        self.tb.insert("1.0", text)
        self.tb.bind("<Return>", lambda e: (self._ok(), "break")[1])

        self.section_link = FormSection(self, "画师链接（可选）")
        self.section_link.pack(fill="x", padx=20, pady=6)
        self.e_link = ctk.CTkEntry(self.section_link, height=38,
                                   placeholder_text="Pixiv / Twitter / ...", **ENTRY_STYLE)
        self.e_link.pack(fill="x", padx=10, pady=(0, 10))
        if link:
            self.e_link.insert(0, link)

        self.section_weight = FormSection(self, "默认权重")
        self.section_weight.pack(fill="x", padx=20, pady=6)
        weight_row = ctk.CTkFrame(self.section_weight, fg_color="transparent")
        weight_row.pack(fill="x", padx=10, pady=(0, 10))
        weight_row.grid_columnconfigure(0, weight=1)
        self.slider = ctk.CTkSlider(weight_row, from_=0, to=2, number_of_steps=20,
                                    progress_color=COLOR["accent"], button_color=COLOR["accent"],
                                    button_hover_color=COLOR["accent_hover"], fg_color=COLOR["border"],
                                    command=self._set_weight_label)
        self.slider.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.slider.set(float(weight))
        self.lbl_weight = ctk.CTkLabel(weight_row, text=f"{float(weight):.1f}", width=34,
                                       font=font(12, True))
        self.lbl_weight.grid(row=0, column=1)
        self.after(250, self.tb.focus_set)

    def _choose_images(self):
        paths = filedialog.askopenfilenames(
            parent=self, title="选择参考图片（可多选）",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")])
        if paths:
            self.selected_images = list(paths)
            self.lbl_images.configure(text=f"已选择 {len(paths)} 张图片")

    def _set_weight_label(self, value):
        self.lbl_weight.configure(text=f"{round(value, 1):.1f}")

    def _ok(self):
        text = self.tb.get("1.0", "end").replace("\n", " ").strip()
        if not text:
            return self._warn("画师串不能为空")
        labels = [item.strip().lstrip("#") for item in self.e_labels.get().replace("，", ",").split(",")
                  if item.strip()]
        self.result = (text, self.e_link.get().strip(), round(self.slider.get(), 1),
                       self.e_display.get().strip(), labels, self.e_note.get().strip(),
                       self.selected_images)
        self.destroy()


class BatchDialog(BaseDialog):
    def __init__(self, master):
        super().__init__(master, "批量添加（一行一条）", 540, 420)
        self._buttons()
        self._label("每行一个画师串，空行会被忽略")
        self.tb = ctk.CTkTextbox(self, font=font(13), wrap="none",
                                 fg_color=COLOR["input"], text_color=COLOR["text"],
                                 border_color=COLOR["border"], corner_radius=8)
        self.tb.pack(fill="both", expand=True, padx=20)
        self.after(250, self.tb.focus_set)

    def _ok(self):
        lines = [l.strip() for l in self.tb.get("1.0", "end").splitlines() if l.strip()]
        if not lines:
            return self._warn("没有输入内容")
        self.result = lines
        self.destroy()


class MoveDialog(BaseDialog):
    def __init__(self, master, group_names: list, exclude: str):
        super().__init__(master, "移动到分组", 340, 190)
        self._buttons()
        targets = [g for g in group_names if g != exclude]
        self._label("目标分组")
        self.menu = ctk.CTkOptionMenu(
            self, values=targets, height=38, fg_color=COLOR["panel_alt"],
            button_color=COLOR["accent"], button_hover_color=COLOR["accent_hover"],
            text_color=COLOR["text"], corner_radius=8)
        self.menu.pack(fill="x", padx=20)
        if targets:
            self.menu.set(targets[0])

    def _ok(self):
        self.result = self.menu.get()
        self.destroy()
