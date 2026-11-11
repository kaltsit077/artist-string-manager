# Repository Guide

- The maintained application is `app_electron/`. Put new UI, desktop integration, and data access changes there.
- Keep the existing JSON keys and image directory layout compatible. Do not commit local JSON data, images, secrets, Electron binaries, or release output.
- `artist_manager/` is the Python fallback. Change it only for an explicitly requested Python fix or to document compatibility behavior.
- Keep Electron security boundaries: renderer code uses the narrow API in `preload.cjs`; filesystem access stays in `main.cjs` behind validated IPC handlers.
- Keep features separated by responsibility: Electron lifecycle and filesystem operations in `main.cjs`, exposed IPC methods in `preload.cjs`, interaction/state in `renderer.js`, and presentation in `style.css`.
- Update `README.md` or `docs/ARCHITECTURE.md` when changing startup, storage, or module boundaries.
- Before handoff, run `cd app_electron; npm run check`. For packaging changes, also run `npm run pack:dir` and report any network or signing limitations.
