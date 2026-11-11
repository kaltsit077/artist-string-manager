"""数据层：JSON 读写、图片文件夹管理、复制文本拼接。不依赖任何 UI，可单独测试。

目录结构:
    images/<分组目录>/<画师目录>/xxx.png
JSON 中只存相对路径: group["dir"] / tag["folder"]
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
IMG_FILTER = [("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")]

_ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL",
             *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}

SORT_MODES = {
    "手动顺序": "manual",
    "名称 A–Z": "name_asc",
    "名称 Z–A": "name_desc",
    "权重从高到低": "weight_desc",
    "权重从低到高": "weight_asc",
    "稳定打散": "shuffle",
}

def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def open_path(path: Path):
    """跨平台打开文件夹"""
    if sys.platform.startswith("win"):
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def safe_name(text: str, max_len: int = 40) -> str:
    s = _ILLEGAL.sub("_", text)
    s = re.sub(r"\s+", " ", s).strip(" .")
    if not s:
        s = "unnamed"
    if len(s) > max_len:
        s = s[:max_len].rstrip(" .") + "_" + hashlib.md5(text.encode("utf-8")).hexdigest()[:6]
    if s.split(".")[0].upper() in _RESERVED:
        s = "_" + s
    return s


def unique_dir(parent: Path, name: str) -> Path:
    p = parent / name
    i = 2
    while p.exists():
        p = parent / f"{name}_{i}"
        i += 1
    return p


def _remove_identity(lst: list, obj):
    """按对象身份删除（list.remove 按内容比较，遇到内容相同的条目会删错）"""
    for i, x in enumerate(lst):
        if x is obj:
            del lst[i]
            return


class Store:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.json_path = root_dir / "artist_group_tags.json"
        self.img_dir = root_dir / "images"
        self.img_dir.mkdir(exist_ok=True)
        self.groups: dict = {}
        self._first_image_cache: dict[str, tuple[int, Path | None]] = {}

    # ---------------- 读写 ----------------
    def load(self):
        self.groups = {}
        if self.json_path.exists():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.groups = json.load(f)
                if not isinstance(self.groups, dict):
                    raise ValueError("数据文件顶层必须是对象")
            except Exception:
                try:   # 读取失败先备份，避免下次保存把原文件覆盖成空
                    shutil.copy2(self.json_path, self.json_path.with_suffix(".json.bak"))
                except OSError:
                    pass
                self.groups = {}
        self._migrate()

    def save(self):
        tmp = self.json_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.groups, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.json_path)

    # ---------------- 分组 ----------------
    def add_group(self, name: str, prefix: str, suffix: str):
        self.groups[name] = {"prefix": prefix, "suffix": suffix, "sort_mode": "manual", "tags": []}
        self._assign_group_dir(name)
        self.save()

    def rename_group(self, old: str, new: str):
        self.groups = {(new if k == old else k): v for k, v in self.groups.items()}
        self._apply_sort(new)
        self.save()

    def delete_group(self, name: str):
        self._rmtree_safe(self.group_dir(name))
        del self.groups[name]
        self._first_image_cache.clear()
        self.save()

    def group_dir(self, name: str) -> Path:
        return self.img_dir / self.groups[name]["dir"]

    # ---------------- 条目 ----------------
    def add_tags(self, group: str, texts: list[str], link: str = "", weight: float = 1.0,
                 display_name: str = "", labels=None, note: str = ""):
        for t in texts:
            self.groups[group]["tags"].append({
                "text": t, "weight": weight, "link": link, "folder": "",
                "display_name": display_name.strip(),
                "labels": self._normalize_labels(labels), "note": note.strip()})
        self._apply_sort(group)
        self.save()

    def delete_tag(self, group: str, tag: dict):
        if tag.get("folder"):
            self._rmtree_safe(self.root_dir / tag["folder"])
        _remove_identity(self.groups[group]["tags"], tag)
        self.save()

    def move_tag(self, src: str, dst: str, tag: dict):
        _remove_identity(self.groups[src]["tags"], tag)
        self._move_item_folder(tag, dst)
        self.groups[dst]["tags"].append(tag)
        self._apply_sort(dst)
        self.save()

    def copy_tag(self, src: str, dst: str, tag: dict):
        copied = dict(tag)
        copied["folder"] = ""
        if tag.get("folder"):
            source = self.root_dir / tag["folder"]
            if source.is_dir():
                target = unique_dir(self.group_dir(dst), source.name)
                shutil.copytree(source, target)
                copied["folder"] = target.relative_to(self.root_dir).as_posix()
        self.groups[dst]["tags"].append(copied)
        self._apply_sort(dst)
        self.save()

    def export_file(self, path: str | Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.groups, f, ensure_ascii=False, indent=2)

    def set_sort_mode(self, group: str, mode: str):
        if mode not in SORT_MODES.values():
            mode = "manual"
        self.groups[group]["sort_mode"] = mode
        self._apply_sort(group)
        self.save()

    def _apply_sort(self, group: str):
        mode = self.groups[group].get("sort_mode", "manual")
        tags = self.groups[group]["tags"]
        def weight(tag):
            try:
                return float(tag.get("weight", 1.0))
            except (TypeError, ValueError):
                return 1.0
        if mode == "name_asc":
            tags.sort(key=lambda t: (t.get("display_name") or t.get("text", "")).casefold())
        elif mode == "name_desc":
            tags.sort(key=lambda t: (t.get("display_name") or t.get("text", "")).casefold(), reverse=True)
        elif mode == "weight_desc":
            tags.sort(key=weight, reverse=True)
        elif mode == "weight_asc":
            tags.sort(key=weight)
        elif mode == "shuffle":
            # Stable shuffle: the order survives restarts and list refreshes.
            tags.sort(key=lambda t: hashlib.sha256(
                f'{group}\0{t.get("text", "")}\0{t.get("link", "")}\0{t.get("weight", 1.0)}'.encode("utf-8")
            ).digest())

    def import_legacy_file(self, file_path: str | Path) -> tuple[int, int]:
        """Merge a legacy JSON export without replacing any current groups."""
        source = Path(file_path).expanduser().resolve()
        with open(source, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("groups"), dict):
            data = data["groups"]
        if not isinstance(data, dict):
            raise ValueError("旧数据格式无效：需要以分组名称为键的 JSON 对象")

        added_groups = added_tags = 0
        for raw_name, old_group in data.items():
            if not isinstance(old_group, dict) or not isinstance(old_group.get("tags", []), list):
                continue
            base_name = str(raw_name).strip() or "导入分组"
            name = base_name
            suffix = 2
            while name in self.groups:
                name = f"{base_name}（导入 {suffix}）"
                suffix += 1
            self.groups[name] = {
                "prefix": str(old_group.get("prefix", "")),
                "suffix": str(old_group.get("suffix", "")),
                "sort_mode": "manual",
                "tags": [],
            }
            self._assign_group_dir(name)
            added_groups += 1

            for old_tag in old_group.get("tags", []):
                if isinstance(old_tag, str):
                    old_tag = {"text": old_tag}
                if not isinstance(old_tag, dict) or not str(old_tag.get("text", "")).strip():
                    continue
                tag = {
                    "text": str(old_tag["text"]).strip(),
                    "weight": self._safe_weight(old_tag.get("weight", 1.0)),
                    "link": str(old_tag.get("link", "")),
                    "folder": "",
                    "display_name": str(old_tag.get("display_name", "")),
                    "labels": self._normalize_labels(old_tag.get("labels", [])),
                    "note": str(old_tag.get("note", "")),
                }
                self.groups[name]["tags"].append(tag)

                # Bring along legacy image files when their paths resolve beside
                # the selected JSON or inside the current data directory.
                old_asset = old_tag.get("folder") or old_tag.get("img", "")
                if old_asset:
                    asset = Path(str(old_asset))
                    candidates = [asset] if asset.is_absolute() else [source.parent / asset, self.root_dir / asset]
                    resolved = next((p.resolve() for p in candidates if p.exists()), None)
                    if resolved and resolved.is_file() and resolved.suffix.lower() in IMG_EXTS:
                        self.import_images(name, tag, [resolved], persist=False)
                    elif resolved and resolved.is_dir():
                        images = [p for p in resolved.iterdir()
                                  if p.is_file() and p.suffix.lower() in IMG_EXTS]
                        if images:
                            self.import_images(name, tag, images, persist=False)
                added_tags += 1
        if added_groups:
            self.save()
        return added_groups, added_tags

    # ---------------- 复制文本 ----------------
    def format_tag(self, group: str, tag: dict) -> str:
        g = self.groups[group]
        return f"{tag.get('weight', 1.0):.1f}{g['prefix']}{tag['text']}{g['suffix']}"

    def format_tags(self, items: list[tuple[str, dict]], sep: str = ", ") -> str:
        return sep.join(self.format_tag(g, t) for g, t in items)

    @staticmethod
    def _normalize_labels(labels):
        if isinstance(labels, str):
            labels = re.split(r"[,，;；]", labels)
        if not isinstance(labels, (list, tuple)):
            return []
        return list(dict.fromkeys(str(label).strip().lstrip("#")
                                  for label in labels if str(label).strip()))

    # ---------------- 图片 ----------------
    def item_folder(self, group: str, tag: dict) -> Path:
        rel = tag.get("folder")
        if rel and (self.root_dir / rel).is_dir():
            return self.root_dir / rel
        folder = unique_dir(self.group_dir(group), safe_name(tag["text"]))
        folder.mkdir(parents=True)
        tag["folder"] = folder.relative_to(self.root_dir).as_posix()
        return folder

    def first_image(self, tag: dict) -> Path | None:
        rel = tag.get("folder")
        if not rel:
            return None
        folder = self.root_dir / rel
        if not folder.is_dir():
            return None
        try:
            stamp = folder.stat().st_mtime_ns
        except OSError:
            return None
        key = str(folder.resolve())
        cached = self._first_image_cache.get(key)
        if cached and cached[0] == stamp:
            return cached[1]
        image = next(iter(sorted(p for p in folder.iterdir()
                                 if p.is_file() and p.suffix.lower() in IMG_EXTS)), None)
        self._first_image_cache[key] = (stamp, image)
        return image

    def import_images(self, group: str, tag: dict, files, persist: bool = True) -> int:
        folder = self.item_folder(group, tag)
        n = 0
        for f in files:
            src = Path(f)
            if src.resolve().parent == folder.resolve():
                continue
            dst = folder / src.name
            i = 1
            while dst.exists():
                dst = folder / f"{src.stem}_{i}{src.suffix}"
                i += 1
            shutil.copy2(src, dst)
            n += 1
        if persist:
            self.save()
        if n:
            self._first_image_cache.pop(str(folder.resolve()), None)
        return n

    def remove_item_folder(self, tag: dict):
        if tag.get("folder"):
            self._rmtree_safe(self.root_dir / tag["folder"])
        tag["folder"] = ""
        self._first_image_cache.clear()
        self.save()

    # ---------------- 内部 ----------------
    def _assign_group_dir(self, gname: str):
        g = self.groups[gname]
        if g.get("dir"):
            return
        used = {x.get("dir", "").lower() for x in self.groups.values()}
        base = safe_name(gname)
        name, i = base, 2
        while name.lower() in used:
            name = f"{base}_{i}"
            i += 1
        g["dir"] = name

    def _move_item_folder(self, tag: dict, target_group: str):
        rel = tag.get("folder")
        if not rel:
            return
        src = self.root_dir / rel
        if not src.is_dir():
            tag["folder"] = ""
            return
        dst = unique_dir(self.group_dir(target_group), src.name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        tag["folder"] = dst.relative_to(self.root_dir).as_posix()
        self._first_image_cache.clear()

    def _rmtree_safe(self, path: Path):
        """只允许删除 images 目录内部的文件夹"""
        try:
            p = path.resolve()
            p.relative_to(self.img_dir.resolve())
            if p == self.img_dir.resolve():
                return
        except ValueError:
            return
        shutil.rmtree(p, ignore_errors=True)

    def _migrate(self):
        changed = False
        for gname, g in list(self.groups.items()):
            if not isinstance(g, dict):
                del self.groups[gname]
                changed = True
                continue
            for key, default in (("prefix", ""), ("suffix", ""), ("tags", [])):
                if key not in g:
                    g[key] = default
                    changed = True
            if not isinstance(g.get("tags"), list):
                g["tags"] = []
                changed = True
            if g.get("sort_mode") not in SORT_MODES.values():
                g["sort_mode"] = "manual"
                changed = True
            if not g.get("dir"):
                self._assign_group_dir(gname)
                changed = True
            for t in g["tags"]:
                if not isinstance(t, dict):
                    continue
                for key, default in (("folder", ""), ("weight", 1.0), ("link", ""),
                                     ("display_name", ""), ("labels", []), ("note", "")):
                    if key not in t:
                        t[key] = default
                        changed = True
                if "category" in t:
                    t.pop("category", None)
                    changed = True
                labels = self._normalize_labels(t.get("labels"))
                if labels != t.get("labels"):
                    t["labels"] = labels
                    changed = True
                safe_weight = self._safe_weight(t.get("weight"))
                if safe_weight != t.get("weight"):
                    t["weight"] = safe_weight
                    changed = True
                legacy = t.pop("img", "")
                if legacy:
                    changed = True
                if legacy and (self.root_dir / legacy).is_file():
                    src = self.root_dir / legacy
                    dst = self.item_folder(gname, t) / src.name
                    if not dst.exists():
                        shutil.move(str(src), str(dst))
        if changed:
            self.save()

    @staticmethod
    def _safe_weight(value) -> float:
        try:
            return max(0.0, min(2.0, round(float(value), 1)))
        except (TypeError, ValueError):
            return 1.0
