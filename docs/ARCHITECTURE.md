# Architecture

## Runtime

The application is a single-window Electron desktop program. The renderer is plain JavaScript and HTML; Electron owns native dialogs, clipboard access, filesystem operations, and window-level settings.

```text
UI event
  -> app_electron/renderer.js
  -> window.artistApp API from app_electron/preload.cjs
  -> validated IPC handler in app_electron/main.cjs
  -> JSON files / images / operating-system capability
```

The renderer must not access Node APIs directly. Extend the preload API narrowly and validate paths in the main process before file operations. The long tag list is virtualized in the renderer; keep work proportional to visible cards.

## Persistence contract

- `artist_group_tags.json` is the canonical group and tag store.
- `artist_combo_history.json` stores saved output snapshots.
- Image paths in tags remain relative to the app data root and point inside `images/`.
- Existing Python data is read in place when present; imported JSON may include an adjacent image path, which is copied into the managed image tree.
- Never replace a corrupt data file with an empty store without first preserving a backup.

## Modules

- `main.cjs`: app lifecycle, persistence, safe filesystem operations, dialogs, clipboard, external links, and always-on-top.
- `preload.cjs`: minimal renderer capability bridge.
- `renderer.js`: app state, dialogs, virtualized cards, search, combination composition, and UI events.
- `index.html` / `style.css`: structure and visual system.
- `artist_manager/`: historical Python implementation kept for fallback and reference.

## Generated files

`node_modules/`, Electron caches, Python environments, build output, user data, and release directories are local artifacts and must stay out of Git.
