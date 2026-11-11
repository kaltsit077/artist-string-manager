const { contextBridge, ipcRenderer, webUtils } = require('electron');
contextBridge.exposeInMainWorld('artistApp', {
  snapshot: () => ipcRenderer.invoke('data:snapshot'), save: g => ipcRenderer.invoke('groups:save',g),
  deleteGroup: n => ipcRenderer.invoke('groups:delete',n), pickImages: m => ipcRenderer.invoke('images:files',m),
  importImages: (g,t,f) => ipcRenderer.invoke('images:import',g,t,f), firstImage: p => ipcRenderer.invoke('images:first',p),
  clearImages: p => ipcRenderer.invoke('images:clear',p), moveImages: (p,g,c) => ipcRenderer.invoke('images:move',p,g,c), importLegacy: () => ipcRenderer.invoke('dialog:import'),
  exportData: () => ipcRenderer.invoke('dialog:export'), openFolder: p => ipcRenderer.invoke('dialog:open-folder',p),
  openLink: u => ipcRenderer.invoke('dialog:open-link',u), copy: t => ipcRenderer.invoke('clipboard:write',t),
  topmost: v => ipcRenderer.invoke('window:topmost',v), root: () => ipcRenderer.invoke('store:root'),
  loadHistory: () => ipcRenderer.invoke('history:load'), saveHistory: h => ipcRenderer.invoke('history:save',h),
  filePath: file => webUtils.getPathForFile(file)
});
