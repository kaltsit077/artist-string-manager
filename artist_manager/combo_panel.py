"""Artist combination composer with saved combination history."""
import json
from datetime import datetime
from pathlib import Path
from tkinter import messagebox as mb
import customtkinter as ctk
from theme import (APP_BG, CARD_BG, COLOR, PRIMARY_BTN, RADIUS, SECONDARY,
                   SEPARATOR, SUBTLE, HiddenScrollbarFrame, font)


class ComboPanel(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=COLOR["panel"], corner_radius=RADIUS,
                         border_width=1, border_color=COLOR["border"])
        self.app, self.store = app, app.store
        self.items: list[tuple[str, dict]] = []
        self.history_path = self.store.root_dir / "artist_combo_history.json"
        self.history = self._load_history()
        self.loaded_record = None
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(self, text="提示词组合", font=font(19, True), anchor="w",
                     text_color=COLOR["text"]
                     ).grid(row=0, column=0, sticky="ew", pady=(2, 2), padx=4)
        ctk.CTkLabel(self, text="在中间条目点「＋组合」添加，也可一键加入当前分组。",
                     font=font(11), text_color=SUBTLE, anchor="w", wraplength=330
                     ).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.scroll = HiddenScrollbarFrame(self, fg_color="transparent")
        self.scroll.grid(row=2, column=0, sticky="nsew")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", pady=(6, 6))
        ctk.CTkButton(actions, text="加入当前分组", height=30, command=self.select_current,
                      **SECONDARY).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="清空", width=58, height=30, command=self.clear,
                      **SECONDARY).pack(side="left")
        self.ent_sep = ctk.CTkEntry(actions, width=52, height=30)
        self.ent_sep.insert(0, SEPARATOR)
        self.ent_sep.pack(side="right")
        ctk.CTkLabel(actions, text="分隔符", font=font(11), text_color=SUBTLE
                     ).pack(side="right", padx=(0, 5))

        card = ctk.CTkFrame(self, corner_radius=RADIUS, fg_color=CARD_BG,
                            border_width=1, border_color=COLOR["border"])
        card.grid(row=4, column=0, sticky="ew")
        self.txt = ctk.CTkTextbox(card, height=116, wrap="word", font=font(12),
                                  fg_color=COLOR["input"], border_width=0,
                                  text_color=COLOR["text"], corner_radius=RADIUS)
        self.txt.pack(fill="x", padx=9, pady=(9, 6))
        self.txt.configure(state="disabled")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=9, pady=(0, 9))
        self.lbl_count = ctk.CTkLabel(row, text="已选择 0 项", font=font(12), text_color=SUBTLE)
        self.lbl_count.pack(side="left")
        ctk.CTkButton(row, text="编辑组合", width=92, height=32,
                      command=self.edit_combo, **SECONDARY).pack(side="right", padx=(0, 6))
        ctk.CTkButton(row, text="复制组合", width=92, height=32,
                      command=self.copy, **PRIMARY_BTN).pack(side="right")
        ctk.CTkButton(row, text="记录组合", width=92, height=32,
                      command=self.save_record, **SECONDARY).pack(side="right", padx=(0, 6))
        self.ent_sep.bind("<KeyRelease>", lambda _e: self._update())

    def refresh(self):
        owner_by_id = {id(t): g for g, data in self.store.groups.items() for t in data["tags"]}
        self.items = [(owner_by_id[id(t)], t) for _g, t in self.items if id(t) in owner_by_id]
        self._render()

    def add_item(self, group: str, tag: dict):
        if not any(g == group and t is tag for g, t in self.items):
            self.items.append((group, tag))
            self._render()
        self.app.toast("已加入画师组合")

    def remove_item(self, group: str, tag: dict):
        self.items = [(g, t) for g, t in self.items if not (g == group and t is tag)]
        self._render()

    def _render(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.scroll, text="当前组合", anchor="w", font=font(12, True),
                     text_color=SUBTLE).pack(fill="x", padx=4, pady=(4, 2))
        if not self.items:
            ctk.CTkLabel(self.scroll, text="组合列表为空\n从中间列表添加画师串",
                         justify="center", text_color=SUBTLE
                         ).pack(fill="x", pady=28)
        for index, (group, tag) in enumerate(self.items, 1):
            row = ctk.CTkFrame(self.scroll, corner_radius=RADIUS, fg_color=CARD_BG)
            row.pack(fill="x", padx=2, pady=3)
            row.grid_columnconfigure(0, weight=1)
            text = tag.get("text", "")
            if len(text) > 64:
                text = text[:61] + "…"
            ctk.CTkLabel(row, text=f"{index:02d}  {text}", anchor="w", justify="left",
                         wraplength=265, font=font(12)).grid(
                             row=0, column=0, sticky="ew", padx=(10, 4), pady=8)
            ctk.CTkButton(row, text="×", width=30, height=28, **SECONDARY,
                          command=lambda g=group, t=tag: self.remove_item(g, t)
                          ).grid(row=0, column=1, padx=(0, 7), pady=5)
        ctk.CTkLabel(self.scroll, text="已记录组合", anchor="w", font=font(12, True),
                     text_color=SUBTLE).pack(fill="x", padx=4, pady=(12, 2))
        if not self.history:
            ctk.CTkLabel(self.scroll, text="暂无记录", anchor="w", text_color=SUBTLE
                         ).pack(fill="x", padx=8, pady=5)
        for record in reversed(self.history):
            row = ctk.CTkFrame(self.scroll, corner_radius=RADIUS, fg_color=CARD_BG)
            row.pack(fill="x", padx=2, pady=3)
            row.grid_columnconfigure(0, weight=1)
            title = record.get("title") or record.get("created", "组合记录")
            ctk.CTkButton(row, text=title, anchor="w", height=32, **SECONDARY,
                          command=lambda r=record: self.load_record(r)).grid(
                              row=0, column=0, sticky="ew", padx=(6, 3), pady=5)
            ctk.CTkButton(row, text="×", width=30, height=28, **SECONDARY,
                          command=lambda r=record: self.delete_record(r)).grid(
                              row=0, column=1, padx=(0, 7), pady=5)
        self._update()

    def select_current(self):
        group = self.app.current_group
        if not group or group not in self.store.groups:
            return
        for tag in self.store.groups[group]["tags"]:
            if not any(g == group and t is tag for g, t in self.items):
                self.items.append((group, tag))
        self._render()

    def clear(self):
        self.items.clear()
        self._render()

    def _sep(self) -> str:
        return self.ent_sep.get().replace("\\n", "\n")

    def _update(self):
        result = self.store.format_tags(self.items, self._sep()) if self.items else ""
        self.loaded_record = None
        self._set_output(result)
        self.lbl_count.configure(text=f"已选择 {len(self.items)} 项")

    def _set_output(self, result):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", result)
        self.txt.configure(state="disabled")

    def _load_history(self):
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _save_history(self):
        temp = self.history_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.history, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.history_path)

    def save_record(self):
        text = self.txt.get("1.0", "end-1c").strip()
        if not text:
            return self.app.toast("先添加画师串，再记录组合")
        created = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
        self.history.append({"created": created, "title": f"组合 {created}", "text": text})
        try:
            self._save_history()
        except OSError as exc:
            return mb.showerror("记录失败", str(exc), parent=self.app)
        self._render()
        self.app.toast("组合已记录")

    def load_record(self, record):
        self.loaded_record = record
        self._set_output(record.get("text", ""))
        self.lbl_count.configure(text="已载入记录")

    def delete_record(self, record):
        self.history = [item for item in self.history if item is not record]
        try:
            self._save_history()
        except OSError as exc:
            return mb.showerror("删除失败", str(exc), parent=self.app)
        self._render()

    def edit_combo(self):
        if not self.items:
            return self.app.toast("请先添加画师串，再编辑组合")
        dlg = ctk.CTkToplevel(self.app)
        dlg.title("编辑画师组合")
        dlg.configure(fg_color=APP_BG)
        dlg.geometry("900x620")
        dlg.minsize(680, 480)
        dlg.transient(self.app)
        selected, members = list(self.items), list(self.items)
        dlg.grid_columnconfigure(0, weight=1)
        dlg.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(dlg, text="组合画师串", anchor="w", font=font(14, True)
                     ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))
        body = ctk.CTkFrame(dlg, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=18)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=2)
        body.grid_rowconfigure(2, weight=1)
        output = ctk.CTkTextbox(body, wrap="word", font=font(13),
                                fg_color=COLOR["input"], text_color=COLOR["text"],
                                corner_radius=RADIUS)
        output.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        output.configure(state="disabled")
        ctk.CTkLabel(body, text="已加入（拖动可加入，点 × 移回下方）",
                     anchor="w", text_color=SUBTLE).grid(row=1, column=0, sticky="ew", pady=4)
        chosen = ctk.CTkScrollableFrame(body, orientation="horizontal", height=76)
        chosen.grid(row=2, column=0, sticky="nsew")
        ctk.CTkLabel(body, text="可加入的画师（拖到上方组合区）",
                     anchor="w", text_color=SUBTLE).grid(row=3, column=0, sticky="ew", pady=(10, 4))
        available = ctk.CTkScrollableFrame(body, orientation="horizontal", height=100)
        available.grid(row=4, column=0, sticky="ew")
        footer = ctk.CTkFrame(dlg, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=14)

        def show_preview(widget, tag):
            image = self.store.first_image(tag)
            if image:
                self.app.preview.show(str(image), widget.winfo_rootx(), widget.winfo_rooty())

        def drop_to_selected(event, item):
            x, y = event.x_root, event.y_root
            targets = (output, chosen)
            inside = any(
                target.winfo_rootx() <= x <= target.winfo_rootx() + target.winfo_width()
                and target.winfo_rooty() <= y <= target.winfo_rooty() + target.winfo_height()
                for target in targets
            )
            if inside:
                if not any(tag is item[1] for _group, tag in selected):
                    selected.append(item)
                    rebuild()

        def rebuild():
            for child in chosen.winfo_children() + available.winfo_children():
                child.destroy()
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.insert("1.0", self.store.format_tags(selected, self._sep()))
            output.configure(state="disabled")
            chosen_ids = {id(tag) for _group, tag in selected}
            for index, (group, tag) in enumerate(selected, 1):
                chip = ctk.CTkFrame(chosen, corner_radius=8, fg_color=CARD_BG)
                chip.pack(side="left", padx=4, pady=8)
                label = ctk.CTkLabel(chip, text=f"{index}. {tag.get('text', '')}", cursor="hand2")
                label.pack(side="left", padx=(9, 3), pady=7)
                label.bind("<Enter>", lambda e, t=tag: show_preview(e.widget, t))
                label.bind("<Leave>", lambda _e: self.app.preview.hide())
                ctk.CTkButton(chip, text="×", width=26, height=26, **SECONDARY,
                              command=lambda item=(group, tag): remove_selected(item)
                              ).pack(side="left", padx=(0, 5), pady=4)
            for group, tag in members:
                if id(tag) in chosen_ids:
                    continue
                pill = ctk.CTkButton(available, text=tag.get("text", ""), height=34,
                                     width=max(90, min(220, len(tag.get("text", "")) * 9)),
                                     **SECONDARY)
                pill.pack(side="left", padx=4, pady=8)
                pill.bind("<Enter>", lambda e, t=tag: show_preview(e.widget, t))
                pill.bind("<Leave>", lambda _e: self.app.preview.hide())
                pill.bind("<ButtonRelease-1>", lambda e, item=(group, tag): drop_to_selected(e, item))

        def remove_selected(item):
            selected[:] = [pair for pair in selected if pair[1] is not item[1]]
            rebuild()

        def accept():
            self.items = list(selected)
            self._render()
            dlg.destroy()

        ctk.CTkButton(footer, text="取消", width=88, command=dlg.destroy,
                      **SECONDARY).pack(side="right")
        ctk.CTkButton(footer, text="应用", width=88, command=accept,
                      **PRIMARY_BTN).pack(side="right", padx=(0, 8))
        rebuild()

    def copy(self):
        result = self.txt.get("1.0", "end-1c").strip()
        if not result:
            return self.app.toast("请先添加要组合的画师串")
        self.app.copy_text(result)
