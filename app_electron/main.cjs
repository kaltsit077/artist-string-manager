const { app, BrowserWindow, ipcMain, dialog, clipboard, shell } = require('electron');
const { pathToFileURL } = require('node:url');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']);
const SORT_MODES = ['manual', 'name_asc', 'name_desc', 'weight_desc', 'weight_asc', 'shuffle'];
let win;
let rootDir;
let groups = {};
function logError(error) {
  const message = error?.stack || String(error);
  try { fs.appendFileSync(path.join(app.getPath('userData'), 'artist-manager-startup.log'), `${new Date().toISOString()}\n${message}\n\n`, 'utf8'); } catch {}
}
const dataPath = () => path.join(rootDir, 'artist_group_tags.json');
const imageRoot = () => path.join(rootDir, 'images');
const safeName = (s, max = 40) => {
  let name = String(s).replace(/[\\/:*?"<>|\x00-\x1f]/g, '_').replace(/\s+/g, ' ').trim().replace(/[ .]+$/g, '') || 'unnamed';
  if (/^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)/i.test(name)) name = `_${name}`;
  if (name.length > max) name = `${name.slice(0, max - 7).trim()}_${crypto.createHash('md5').update(s).digest('hex').slice(0, 6)}`;
  return name;
};
const uniqueDir = (parent, base) => { let p = path.join(parent, base), i = 2; while (fs.existsSync(p)) p = path.join(parent, `${base}_${i++}`); return p; };
function normalizeLabels(labels) {
  if (typeof labels === 'string') labels = labels.split(/[,，;；]/);
  if (!Array.isArray(labels)) return [];
  return [...new Set(labels.map(x => String(x).trim().replace(/^#/, '')).filter(Boolean))];
}
function normalize() {
  const usedDirs = new Set();
  for (const [name, g] of Object.entries(groups)) {
    if (!g || typeof g !== 'object') { delete groups[name]; continue; }
    g.prefix ??= ''; g.suffix ??= ''; g.tags = Array.isArray(g.tags) ? g.tags : [];
    if (!SORT_MODES.includes(g.sort_mode)) g.sort_mode = 'manual';
    let dir = safeName(g.dir || name);
    const base = dir; let suffix = 2;
    while (usedDirs.has(dir.toLowerCase())) dir = `${base}_${suffix++}`;
    g.dir = dir; usedDirs.add(dir.toLowerCase());
    for (const t of g.tags) {
      if (!t || typeof t !== 'object') continue;
      t.folder ??= ''; const rawWeight = Number(t.weight); t.weight = Math.max(0, Math.min(2, Math.round((Number.isFinite(rawWeight) ? rawWeight : 1) * 10) / 10));
      t.link ??= ''; t.display_name ??= ''; t.labels = normalizeLabels(t.labels); t.note ??= '';
      delete t.category;
      if (t.img) { const old = path.resolve(rootDir, t.img); if (fs.existsSync(old) && fs.statSync(old).isFile()) { const folder = itemFolder(name, t); fs.copyFileSync(old, path.join(folder, path.basename(old))); } delete t.img; }
    }
  }
}
function save() {
  fs.mkdirSync(rootDir, { recursive: true });
  const tmp = `${dataPath()}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(groups, null, 2), 'utf8'); fs.renameSync(tmp, dataPath());
}
function load() {
  fs.mkdirSync(imageRoot(), { recursive: true });
  try { const value = JSON.parse(fs.readFileSync(dataPath(), 'utf8')); groups = value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
  catch (e) { if (e.code !== 'ENOENT') { try { fs.copyFileSync(dataPath(), `${dataPath()}.bak`); } catch {} } groups = {}; }
  normalize(); save();
}
function groupDir(name) { const g = groups[name]; if (!g) throw new Error('分组不存在'); return path.join(imageRoot(), g.dir); }
function itemFolder(group, tag) {
  let folder = tag.folder ? path.resolve(rootDir, tag.folder) : '';
  if (folder && folder.startsWith(`${imageRoot()}${path.sep}`) && fs.existsSync(folder)) return folder;
  fs.mkdirSync(groupDir(group), { recursive: true });
  folder = uniqueDir(groupDir(group), safeName(tag.text)); fs.mkdirSync(folder, { recursive: true });
  tag.folder = path.relative(rootDir, folder).replaceAll('\\', '/'); return folder;
}
function sortGroup(name) {
  const g = groups[name]; const mode = g.sort_mode;
  if (mode === 'name_asc' || mode === 'name_desc') g.tags.sort((a,b) => (a.display_name || a.text).localeCompare(b.display_name || b.text) * (mode === 'name_asc' ? 1 : -1));
  if (mode === 'weight_asc' || mode === 'weight_desc') g.tags.sort((a,b) => (a.weight-b.weight) * (mode === 'weight_asc' ? 1 : -1));
  if (mode === 'shuffle') g.tags.sort((a,b) => crypto.createHash('sha256').update(`${name}\0${a.text}\0${a.link}\0${a.weight}`).digest('hex').localeCompare(crypto.createHash('sha256').update(`${name}\0${b.text}\0${b.link}\0${b.weight}`).digest('hex')));
}
function snapshot() { return { groups, rootDir }; }
function createWindow() {
  win = new BrowserWindow({ width: 1500, height: 920, minWidth: 1120, minHeight: 650, title: '画师串管理器', backgroundColor: '#0b1117', webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true } });
  win.webContents.on('did-fail-load', (_event, code, description, url) => { const error = new Error(`Renderer load failed (${code}): ${description}; ${url}`); logError(error); dialog.showErrorBox('画师串管理器启动失败', error.message); });
  win.webContents.on('console-message', (_event, details) => { if (details.level >= 2) logError(new Error(`Renderer: ${details.message} (${details.sourceId}:${details.lineNumber})`)); });
  win.loadFile(path.join(__dirname, 'index.html'));
}
process.on('uncaughtException', error => { logError(error); dialog.showErrorBox('画师串管理器启动失败', error?.message || String(error)); });
app.whenReady().then(() => { const legacyRoot = app.isPackaged ? path.dirname(app.getPath('exe')) : path.join(__dirname, '..', 'artist_manager'); rootDir = fs.existsSync(path.join(legacyRoot,'artist_group_tags.json')) || app.isPackaged ? legacyRoot : path.join(__dirname, 'data'); load(); createWindow(); app.on('activate', () => { if (!BrowserWindow.getAllWindows().length) createWindow(); }); }).catch(error => { logError(error); dialog.showErrorBox('画师串管理器启动失败', error?.message || String(error)); app.quit(); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });

ipcMain.handle('data:snapshot', () => snapshot());
ipcMain.handle('groups:save', (_e, next) => { groups = next; normalize(); save(); return snapshot(); });
ipcMain.handle('groups:delete', (_e, name) => {
  const dir = path.resolve(groupDir(name)); if (dir.startsWith(`${imageRoot()}${path.sep}`)) fs.rmSync(dir, { recursive: true, force: true });
  delete groups[name]; save(); return snapshot();
});
ipcMain.handle('images:files', async (_e, multiple = true) => {
  const result = await dialog.showOpenDialog(win, { properties: multiple ? ['openFile','multiSelections'] : ['openFile'], filters: [{ name: '图片', extensions: [...IMAGE_EXTS].map(x => x.slice(1)) }] }); return result.canceled ? [] : result.filePaths;
});
ipcMain.handle('images:import', (_e, group, tag, files) => {
  const folder = itemFolder(group, tag); let count = 0;
  for (const src of files) { if (!IMAGE_EXTS.has(path.extname(src).toLowerCase()) || !fs.existsSync(src)) continue; let target = path.join(folder, path.basename(src)), i = 1; while (fs.existsSync(target)) target = path.join(folder, `${path.parse(src).name}_${i++}${path.extname(src)}`); if (path.resolve(src) !== path.resolve(target)) { fs.copyFileSync(src, target); count++; } }
  save(); return { count, folder: tag.folder };
});
ipcMain.handle('images:first', (_e, rel) => { if (!rel) return null; const folder = path.resolve(rootDir, rel); if (!folder.startsWith(`${imageRoot()}${path.sep}`) || !fs.existsSync(folder)) return null; const file = fs.readdirSync(folder).filter(f => IMAGE_EXTS.has(path.extname(f).toLowerCase())).sort()[0]; return file ? pathToFileURL(path.join(folder,file)).href : null; });
ipcMain.handle('images:clear', (_e, rel) => { if (rel) { const folder = path.resolve(rootDir,rel); if (folder.startsWith(`${imageRoot()}${path.sep}`)) fs.rmSync(folder,{recursive:true,force:true}); } return true; });
ipcMain.handle('images:move', (_e, rel, targetGroup, copy) => { if (!rel || !groups[targetGroup]) return ''; const src=path.resolve(rootDir,rel); if(!src.startsWith(`${imageRoot()}${path.sep}`)||!fs.existsSync(src))return ''; const parent=groupDir(targetGroup);fs.mkdirSync(parent,{recursive:true});const dst=uniqueDir(parent,path.basename(src));if(copy)fs.cpSync(src,dst,{recursive:true});else fs.renameSync(src,dst);return path.relative(rootDir,dst).replaceAll('\\','/'); });
ipcMain.handle('dialog:import', async () => {
  const r = await dialog.showOpenDialog(win, { properties: ['openFile'], filters: [{ name: 'JSON 数据', extensions: ['json'] }] });
  if (r.canceled) return null;
  const sourcePath = r.filePaths[0];
  const raw = JSON.parse(fs.readFileSync(sourcePath, 'utf8').replace(/^\uFEFF/, ''));
  const incoming = raw?.groups && typeof raw.groups === 'object' ? raw.groups : raw;
  let addedGroups = 0, addedTags = 0;
  for (const [base, old] of Object.entries(incoming || {})) {
    if (!old || !Array.isArray(old.tags)) continue;
    let name = base.trim() || '导入分组', i = 2;
    while (groups[name]) name = `${base}（导入 ${i++}）`;
    groups[name] = { prefix: old.prefix || '', suffix: old.suffix || '', sort_mode: 'manual', dir: safeName(name), tags: [] };
    const tags = [];
    for (const oldTag of old.tags) {
      if (!(typeof oldTag === 'string' || oldTag?.text)) continue;
      const sourceTag = typeof oldTag === 'string' ? { text: oldTag } : oldTag;
      const tag = { ...sourceTag, text: String(sourceTag.text).trim(), weight: Number(sourceTag.weight) || 1,
        link: sourceTag.link || '', display_name: sourceTag.display_name || '', labels: normalizeLabels(sourceTag.labels),
        note: sourceTag.note || '', folder: '' };
      const assetRel = sourceTag.folder || sourceTag.img || '';
      if (assetRel) {
        let asset = path.resolve(path.dirname(sourcePath), assetRel);
        if (!fs.existsSync(asset)) asset = path.resolve(rootDir, assetRel);
        if (fs.existsSync(asset)) {
          const target = itemFolder(name, tag);
          if (fs.statSync(asset).isDirectory()) {
            for (const file of fs.readdirSync(asset)) if (IMAGE_EXTS.has(path.extname(file).toLowerCase())) {
              const dest = path.join(target, path.basename(file)); if (!fs.existsSync(dest)) fs.copyFileSync(path.join(asset, file), dest);
            }
          } else if (IMAGE_EXTS.has(path.extname(asset).toLowerCase())) {
            const dest = path.join(target, path.basename(asset)); if (!fs.existsSync(dest)) fs.copyFileSync(asset, dest);
          }
        }
      }
      tags.push(tag);
    }
    groups[name].tags = tags;
    addedGroups++; addedTags += tags.length;
  }
  save(); return { addedGroups, addedTags, snapshot: snapshot() };
});
ipcMain.handle('dialog:export', async () => { const r=await dialog.showSaveDialog(win,{defaultPath:'artist_group_tags.json',filters:[{name:'JSON 数据',extensions:['json']}]}); if(r.canceled)return false; fs.writeFileSync(r.filePath,JSON.stringify(groups,null,2),'utf8'); return true; });
ipcMain.handle('dialog:open-folder', (_e, rel) => { if (!rel) return; const p=path.resolve(rootDir,rel); if(p.startsWith(`${imageRoot()}${path.sep}`)&&fs.existsSync(p))shell.openPath(p); });
ipcMain.handle('dialog:open-link', (_e,url) => { if(/^https?:\/\//i.test(url))shell.openExternal(url); });
ipcMain.handle('clipboard:write', (_e,text) => clipboard.writeText(text));
ipcMain.handle('window:topmost', (_e,value) => win?.setAlwaysOnTop(Boolean(value)));
ipcMain.handle('store:root', () => rootDir);
ipcMain.handle('history:load', () => { try { return JSON.parse(fs.readFileSync(path.join(rootDir,'artist_combo_history.json'),'utf8')); } catch { return []; } });
ipcMain.handle('history:save', (_e, items) => { const p=path.join(rootDir,'artist_combo_history.json'), tmp=`${p}.tmp`; fs.writeFileSync(tmp,JSON.stringify(items,null,2),'utf8'); fs.renameSync(tmp,p); return true; });
