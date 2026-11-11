"""主窗口：分组、条目与组合三栏布局。"""
import tkinter.messagebox as mb
from tkinter import filedialog
import customtkinter as ctk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DnDMixin = TkinterDnD.DnDWrapper
    _HAS_DND = True
except ImportError:
    DND_FILES = None
    _DnDMixin = object
    _HAS_DND = False

from combo_panel import ComboPanel
from dialogs import BatchDialog, EditTagDialog, GroupDialog
from preview import PreviewWin
from store import SORT_MODES, Store, app_dir
from tag_row import TagRow
from theme import (APP_BG, SIDEBAR_BG, PANEL_BG, COLOR, ENTRY_STYLE, PRIMARY_BTN,
                   SECONDARY, DANGER_BTN, SUBTLE, HiddenScrollbarFrame, font)

_APP_BASES = (ctk.CTk, _DnDMixin) if _HAS_DND else (ctk.CTk,)
RENDER_BATCH = 12


class MainApp(*_APP_BASES):
    def __init__(self, root_dir=None):
        super().__init__()
        self.title("画师串管理器")
        self.configure(fg_color=APP_BG)
        self.geometry("1460x880")
        self.minsize(1260, 680)
        self._dnd_enabled = False
        if _HAS_DND:
            try:
                TkinterDnD._require(self)
                self._dnd_enabled = True
            except Exception:
                pass

        self.store = Store(root_dir or app_dir())
        self.store.load()
        self.current_group: str | None = None
        self.preview = PreviewWin(self)
        self._render_job = None
        self._render_generation = 0
        self._visible_tags = []
        self._render_items = []
        self._render_cursor = 0
        self._group_cards = {}
        self._search_cards = []
        self._empty_label = None
        self._expanded_groups = True
        self._search_job = None
        self._toast_job = None

        self._build()
        self.refresh_groups(eager_current=False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =================== 布局 ===================
    def _build(self):
        self.grid_columnconfigure(0, weight=0, minsize=190)
        self.grid_columnconfigure(1, weight=3, minsize=560)
        self.grid_columnconfigure(2, weight=2, minsize=320)
        self.grid_rowconfigure(0, weight=1)

        # ---- 侧边栏 ----
        side = ctk.CTkFrame(self, width=224, corner_radius=0, fg_color=SIDEBAR_BG,
                            border_width=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        side.grid_rowconfigure(2, weight=1)
        side.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(side, text="画师串管理器", font=font(18, True), anchor="w",
                     text_color=COLOR["text"]
                     ).grid(row=0, column=0, padx=18, pady=(22, 16), sticky="ew")
        group_head = ctk.CTkFrame(side, fg_color="transparent")
        group_head.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 0))
        group_head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(group_head, text="我的分组", anchor="w", font=font(12, True),
                     text_color=SUBTLE).grid(row=0, column=0, sticky="w", padx=8)
        self.btn_groups_toggle = ctk.CTkButton(
            group_head, text="⌄", width=30, height=28, **SECONDARY,
            command=self.toggle_groups)
        self.btn_groups_toggle.grid(row=0, column=1, sticky="e")
        self.group_list = HiddenScrollbarFrame(side, fg_color="transparent")
        self.group_list.grid(row=2, column=0, sticky="nsew", padx=6)
        ctk.CTkButton(side, text="＋ 新建分组", height=38, command=self.create_group,
                      **PRIMARY_BTN
                      ).grid(row=3, column=0, padx=12, pady=(10, 8), sticky="ew")
        ctk.CTkButton(side, text="导入旧数据…", height=32, command=self.import_legacy,
                      **SECONDARY).grid(row=4, column=0, padx=12, pady=(0, 8), sticky="ew")
        ctk.CTkButton(side, text="导出数据…", height=32, command=self.export_data,
                      **SECONDARY).grid(row=5, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.sw_top = ctk.CTkSwitch(side, text="窗口置顶", command=self._toggle_top)
        self.sw_top.grid(row=6, column=0, padx=16, pady=(0, 16), sticky="w")

        # ---- 主区域 ----
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=(16, 10), pady=(16, 8))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        head = ctk.CTkFrame(main, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew")
        head.grid_columnconfigure(0, weight=1)
        self.lbl_title = ctk.CTkLabel(head, text="", font=font(22, True), anchor="w",
                                      text_color=COLOR["text"])
        self.lbl_title.grid(row=0, column=0, sticky="ew")
        self.lbl_sub = ctk.CTkLabel(head, text="", font=font(12), text_color=COLOR["muted"], anchor="w")
        self.lbl_sub.grid(row=1, column=0, sticky="ew")
        hb = ctk.CTkFrame(head, fg_color="transparent")
        hb.grid(row=0, column=1, rowspan=2)
        ctk.CTkButton(hb, text="编辑分组", width=84, height=32, command=self.edit_group,
                      **SECONDARY).pack(side="left", padx=4)
        ctk.CTkButton(hb, text="删除分组", width=84, height=32, command=self.delete_group,
                      **DANGER_BTN).pack(side="left")

        tb = ctk.CTkFrame(main, fg_color="transparent")
        tb.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        tb.grid_columnconfigure(0, weight=1)
        self.ent_search = ctk.CTkEntry(tb, height=38, placeholder_text="搜索全部分组的标签 / 链接…",
                                       **ENTRY_STYLE)
        self.ent_search.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.ent_search.bind("<KeyRelease>", lambda e: self._debounce_search())
        self.lbl_count = ctk.CTkLabel(tb, text="", font=font(12), text_color=SUBTLE)
        self.lbl_count.grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(tb, text="＋ 新增", width=72, height=34, command=self.add_single
                      ).grid(row=0, column=2, padx=3)
        ctk.CTkButton(tb, text="批量添加", width=84, height=34, command=self.batch_add,
                      **SECONDARY).grid(row=0, column=3, padx=3)
        self.sort_menu = ctk.CTkOptionMenu(
            tb, values=list(SORT_MODES), width=148, height=38, command=self.sort,
            fg_color=COLOR["panel_alt"], button_color=COLOR["accent"],
            button_hover_color=COLOR["accent_hover"], text_color=COLOR["text"],
            corner_radius=8)
        self.sort_menu.grid(row=0, column=4, padx=(6, 0))

        self.list_frame = HiddenScrollbarFrame(
            main, fg_color=PANEL_BG, corner_radius=14, border_width=1,
            border_color=COLOR["border"])
        self.list_frame.grid(row=2, column=0, sticky="nsew")
        self.list_frame._parent_canvas.bind("<MouseWheel>", self._on_list_scroll, add="+")
        self.list_frame._parent_canvas.bind("<Button-4>", self._on_list_scroll, add="+")
        self.list_frame._parent_canvas.bind("<Button-5>", self._on_list_scroll, add="+")
        self.list_frame._parent_canvas.bind("<Configure>", self._on_list_scroll, add="+")

        self.combo = ComboPanel(self, self)
        self.combo.grid(row=0, column=2, sticky="nsew", padx=(8, 16), pady=(16, 8))

        self.status = ctk.CTkLabel(self, text="", anchor="w", font=font(12), text_color=SUBTLE)
        self.status.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(18, 18), pady=(0, 6))

    # =================== 通用 ===================
    def copy_text(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()        # 让剪贴板内容立即生效
        short = text if len(text) <= 70 else text[:70] + "…"
        self.toast(f"已复制：{short}")

    def toast(self, msg: str, ms: int = 3500):
        self.status.configure(text=msg)
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(ms, lambda: self.status.configure(text=""))

    def _toggle_top(self):
        self.attributes("-topmost", bool(self.sw_top.get()))

    def register_drop_target(self, widget, callback):
        if not self._dnd_enabled:
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", callback)
        except Exception:
            pass

    def _on_close(self):
        self.preview.destroy()
        self.destroy()

    def toggle_groups(self):
        self._expanded_groups = not self._expanded_groups
        if self._expanded_groups:
            self.group_list.grid()
            self.btn_groups_toggle.configure(text="⌄")
        else:
            self.group_list.grid_remove()
            self.btn_groups_toggle.configure(text="›")

    # =================== 分组 ===================
    def refresh_groups(self, eager_current=True):
        self._cancel_render()
        # Data mutations invalidate the small in-memory view cache.
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._group_cards.clear()
        self._search_cards.clear()
        self._empty_label = None
        names = list(self.store.groups.keys())
        if self.current_group not in names:
            self.current_group = names[0] if names else None
        for w in self.group_list.winfo_children():
            w.destroy()
        for n in names:
            sel = n == self.current_group
            count = len(self.store.groups[n]["tags"])
            ctk.CTkButton(
                self.group_list, text=f"{n}   ({count})", anchor="w", height=36,
                fg_color=COLOR["accent_soft"] if sel else "transparent",
                hover_color=COLOR["card_hover"],
                text_color=COLOR["text"] if sel else COLOR["text_soft"],
                corner_radius=9, border_width=0,
                command=lambda n=n: self.select_group(n)).pack(fill="x", pady=2)
        self._update_header()
        self._update_sort_menu()
        self.render_list()
        if hasattr(self, "combo"):
            self.combo.refresh()

    def _cancel_render(self):
        self._render_generation += 1
        if self._render_job is not None:
            try:
                self.after_cancel(self._render_job)
            except Exception:
                pass
            self._render_job = None

    def _update_sort_menu(self):
        if not self.current_group:
            return
        mode = self.store.groups[self.current_group].get("sort_mode", "manual")
        label = next((name for name, value in SORT_MODES.items() if value == mode), "手动顺序")
        self.sort_menu.set(label)

    def select_group(self, name: str):
        if name == self.current_group:
            return
        self.current_group = name
        self.ent_search.delete(0, "end")
        self._update_header()
        self._update_sort_menu()
        for button, group_name in zip(self.group_list.winfo_children(), self.store.groups):
            selected = group_name == name
            button.configure(fg_color=COLOR["accent_soft"] if selected else "transparent",
                             text_color=COLOR["text"] if selected else COLOR["text_soft"])
        self.render_list()

    def _update_header(self):
        g = self.store.groups.get(self.current_group)
        if not g:
            self.lbl_title.configure(text="还没有分组")
            self.lbl_sub.configure(text="点击左下角「新建分组」开始")
            return
        self.lbl_title.configure(text=self.current_group)
        self.lbl_sub.configure(
            text=f'前缀 "{g["prefix"]}"    后缀 "{g["suffix"]}"    输出示例：1.0{g["prefix"]}画师串{g["suffix"]}')

    def create_group(self):
        res = GroupDialog(self).run()
        if not res:
            return
        name, pre, suf = res
        if name in self.store.groups:
            return mb.showwarning("提示", "分组已存在", parent=self)
        self.store.add_group(name, pre, suf)
        self.current_group = name
        self.refresh_groups()

    def edit_group(self):
        if not self.current_group:
            return
        g = self.store.groups[self.current_group]
        res = GroupDialog(self, self.current_group, g["prefix"], g["suffix"]).run()
        if not res:
            return
        name, pre, suf = res
        old = self.current_group
        if name != old:
            if name in self.store.groups:
                return mb.showwarning("提示", "分组名重复", parent=self)
            self.store.rename_group(old, name)
            self.current_group = name
        g = self.store.groups[self.current_group]
        g["prefix"], g["suffix"] = pre, suf
        self.store.save()
        self.refresh_groups()

    def delete_group(self):
        if not self.current_group:
            return
        if mb.askyesno("确认", f"确定删除分组【{self.current_group}】？\n"
                              "分组内所有条目及图片文件夹都会删除！", parent=self):
            self.store.delete_group(self.current_group)
            self.current_group = None
            self.refresh_groups()

    # =================== 条目列表 ===================
    def render_list(self):
        self._cancel_render()
        self.preview.hide()
        if self._empty_label is not None:
            self._empty_label.destroy()
            self._empty_label = None
        for cards in self._group_cards.values():
            for _tag, card in cards:
                card.grid_remove()
        for card in self._search_cards:
            card.destroy()
        self._search_cards.clear()
        self.list_frame._parent_canvas.yview_moveto(0)
        self._visible_tags = []
        self._render_items = []
        self._render_cursor = 0
        self.list_frame.grid_columnconfigure(0, weight=1, uniform="tag-cards")
        self.list_frame.grid_columnconfigure(1, weight=1, uniform="tag-cards")
        if not self.current_group:
            self.lbl_count.configure(text="")
            self._empty_label = ctk.CTkLabel(
                self.list_frame, text="先创建分组，再添加提示词记录", text_color=SUBTLE)
            self._empty_label.grid(row=0, column=0, columnspan=2, pady=40)
            return
        kw = self.ent_search.get().strip().lower()
        if kw:
            matches = [(group, tag) for group, data in self.store.groups.items()
                       for tag in data["tags"] if self._matches(tag, kw)]
            self.lbl_count.configure(text=f"{len(matches)} 条 · 全部分组")
            self._render_items = matches
            self._render_target = "search"
        else:
            self._render_items = [(self.current_group, tag)
                                  for tag in self.store.groups[self.current_group]["tags"]]
            self.lbl_count.configure(text=f"{len(self._render_items)} 条")
            self._render_target = self.current_group
            cached = self._group_cards.get(self.current_group)
            if cached is not None:
                for index, (_tag, card) in enumerate(cached):
                    card.grid(row=index // 2, column=index % 2, sticky="ew",
                              padx=6, pady=5)
                    self._visible_tags.append(_tag)
                self._render_cursor = len(cached)
                if self._render_cursor >= len(self._render_items):
                    return

        if not self._render_items:
            self._empty_label = ctk.CTkLabel(self.list_frame, text="没有匹配记录",
                                             text_color=SUBTLE)
            self._empty_label.grid(row=0, column=0, columnspan=2, pady=40)
            return
        generation = self._render_generation
        self._render_cursor = 0
        self._render_job = self.after(35, lambda: self._render_chunk(generation))

    @staticmethod
    def _matches(tag, query):
        return (query in tag.get("text", "").lower()
                or query in tag.get("display_name", "").lower()
                or query in tag.get("link", "").lower()
                or query in tag.get("note", "").lower()
                or any(query in label.lower() for label in tag.get("labels", [])))

    def _render_chunk(self, generation):
        if generation != self._render_generation:
            return
        self._render_job = None
        end = min(self._render_cursor + RENDER_BATCH, len(self._render_items))
        for index, (group, tag) in enumerate(self._render_items[self._render_cursor:end],
                                              self._render_cursor):
            card = TagRow(self.list_frame, self, group, tag)
            card.grid(row=index // 2, column=index % 2, sticky="ew",
                      padx=6, pady=5)
            self._visible_tags.append(tag)
            if self._render_target == "search":
                self._search_cards.append(card)
            else:
                self._group_cards.setdefault(self._render_target, []).append((tag, card))
        self._render_cursor = end
        if end < len(self._render_items):
            # Continue only while the viewport still has empty space or the
            # user scrolls close to the bottom. Large groups stay cheap to open.
            self._render_job = self.after(120, lambda: self._load_more_if_needed(generation))

    def _on_list_scroll(self, _event=None):
        generation = self._render_generation
        if self._render_job is None and self._render_cursor < len(self._render_items):
            self._render_job = self.after(80, lambda: self._load_more_if_needed(generation))

    def _load_more_if_needed(self, generation):
        self._render_job = None
        if generation != self._render_generation or self._render_cursor >= len(self._render_items):
            return
        if self.list_frame._parent_canvas.yview()[1] >= 0.98:
            self._render_chunk(generation)

    def _debounce_search(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(200, self.render_list)

    def add_single(self):
        if not self.current_group:
            return self.toast("请先新建分组")
        res = EditTagDialog(self, "新增记录").run()
        if res:
            self.store.add_tags(self.current_group, [res[0]], res[1], res[2],
                                res[3], res[4], res[5])
            tag = self.store.groups[self.current_group]["tags"][-1]
            if res[6]:
                self.store.import_images(self.current_group, tag, res[6])
            self.refresh_groups()
            if res[6]:
                self.toast(f"已添加记录并导入 {len(res[6])} 张图片")

    def batch_add(self):
        if not self.current_group:
            return self.toast("请先新建分组")
        lines = BatchDialog(self).run()
        if lines:
            self.store.add_tags(self.current_group, lines)
            self.refresh_groups()
            self.toast(f"已添加 {len(lines)} 条")

    def sort(self, mode_label=None):
        if self.current_group:
            mode = SORT_MODES.get(mode_label or self.sort_menu.get(), "manual")
            self.store.set_sort_mode(self.current_group, mode)
            for _tag, card in self._group_cards.pop(self.current_group, []):
                card.destroy()
            self.render_list()

    def import_legacy(self):
        filename = filedialog.askopenfilename(
            parent=self, title="导入旧版数据", filetypes=[("JSON 数据", "*.json"), ("所有文件", "*.*")])
        if not filename:
            return
        try:
            groups, tags = self.store.import_legacy_file(filename)
        except (OSError, ValueError, TypeError) as exc:
            return mb.showerror("导入失败", f"无法导入该文件：\n{exc}", parent=self)
        self.refresh_groups()
        self.toast(f"已导入 {groups} 个分组、{tags} 条画师串")

    def export_data(self):
        filename = filedialog.asksaveasfilename(
            parent=self, title="导出画师数据", defaultextension=".json",
            filetypes=[("JSON 数据", "*.json")], initialfile="artist_group_tags.json")
        if not filename:
            return
        try:
            self.store.export_file(filename)
        except OSError as exc:
            return mb.showerror("导出失败", str(exc), parent=self)
        self.toast("数据已导出")
