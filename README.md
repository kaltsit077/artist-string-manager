# 画师串管理器

Windows 桌面应用，用于管理画师提示词、参考图片，并组合和复制提示词。

## 当前版本

JavaScript / Electron 实现位于 [`app_electron/`](app_electron/)。旧 Python 版本保留在 [`artist_manager/`](artist_manager/) 作为迁移期间的回退实现，不再作为新功能的主要开发目标。

## 本地开发

需要 Node.js 22 或更新版本。

```powershell
cd app_electron
npm ci
npm start
```

首次安装 Electron 时需要下载 Electron 桌面运行时。构建 Windows 运行目录：

```powershell
npm run pack:dir
```

项目根目录的 `启动画师串管理器JS版.bat` 启动最近生成的 Windows 运行目录。

## 数据

应用沿用 `artist_group_tags.json`、`artist_combo_history.json` 和 `images/<分组>/<条目>/` 格式。数据文件与图片属于本地用户数据，不提交到仓库。

## 目录结构

```text
app_electron/       Electron 主进程、预加载脚本和界面
artist_manager/     旧 Python 版回退源码
docs/               架构和维护说明
.cursor/rules/      仓库级编码约定
.github/workflows/  自动化检查
```

## 检查

```powershell
cd app_electron
npm run check
```
