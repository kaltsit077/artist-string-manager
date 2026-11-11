# 画师串管理器（JavaScript 版）

桌面壳使用 Electron，界面使用原生 JavaScript 和 DOM 虚拟列表。启动前安装依赖：

```powershell
npm install
npm start
```

开发运行时优先读取旧版 `artist_manager/artist_group_tags.json`；若该文件不存在，则使用本目录的 `data` 目录。打包后从 exe 同目录读取 `artist_group_tags.json` 和 `images/`，可以直接沿用旧版便携包的数据布局。

数据和组合历史仍保存为 `artist_group_tags.json`、`artist_combo_history.json`。图片继续使用 `images/<分组目录>/<条目目录>/` 布局。原 Python 源码保留为迁移期间的回退版本。
