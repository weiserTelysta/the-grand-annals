# 龙冠枯荣 / The Grand Annals

《龙冠枯荣》是以架空文明史、世界法则与人物命运为核心的中文幻想纪年项目。本仓库将内容创作与网站呈现分离：日常写作只在 `docs` 这座 Obsidian 库中进行，MkDocs 的 UI、SEO 与自动生成逻辑由仓库外层维护。

- 当前唯一正式版本：简体中文
- 正式英文名：The Grand Annals
- 公开站点：<https://annals.telysta.com/>
- 公开中文内容：`docs/zh/`
- 私人原始资料：`docs/weiser/`（不会进入公开构建）
- 网站主题：`overrides/assets/`
- 内容自动化：`tools/mkdocs_hooks.py`

## 在 Obsidian 中写作

请把仓库中的 `docs` 文件夹单独作为 Obsidian 库打开，而不是打开整个仓库。

这个内容库已经配置：

- 新链接使用相对 Markdown 链接，移动文件时自动更新；
- `_templates` 提供通用、人物、地理、法则、历史与私人草稿模板；
- `内容工作台.base` 汇总公开内容、缺少简介、缺少关联、私人草稿和最近修改；
- 网站导航、条目索引和文末相关条目均自动生成，不需要在正文里写 UI HTML。

完整的新建流程见 Obsidian 库中的 `创作工作流.md`。

### 新建公开条目

1. 在 `docs/zh/` 的对应栏目中新建与条目同名的 Markdown 文件。
2. 在命令面板执行“模板：插入模板”，选择最接近的条目模板。
3. 填写 `description`，再开始写正文。
4. 如需文末关联卡片，在 `related` 中添加条目名或带引号的 Obsidian 链接，例如 `"[[长域]]"`。
5. 执行严格构建。新条目会自动加入左侧导航与条目索引。

日常写作不需要修改 `mkdocs.yml`、`docs/zh/索引/index.md`、HTML、CSS 或 JavaScript。

## 本地预览

Windows 首次运行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m mkdocs serve --config-file mkdocs.yml
```

终端出现 `Serving on http://127.0.0.1:8000/` 后，在浏览器打开该地址。`.venv` 已存在时，只需执行最后一行。

发布前执行完整检查：

```powershell
.\.venv\Scripts\python.exe -m mkdocs build --strict --clean --config-file mkdocs.yml
.\.venv\Scripts\python.exe tools\validate_site.py site
```

## 内容模型

公开页至少需要 `title` 与 `description`。`status` 和栏目类型可由目录中的 `.meta.yml` 继承；模板仍会写入这些字段，方便在 Obsidian 的属性面板和 Base 中查看。

```yaml
---
title: 条目名称
description: 一句话说明该条目对陌生读者的价值。
type: 人物
status: 公开
tags:
  - 人物
related:
  - "[[相关条目]]"
---
```

- `tags` 是编辑与检索元数据，当前不在正文中展示。
- `related` 会生成读者可见的文末关联卡片。
- `description` 同时用于索引说明、搜索摘要和 SEO。
- 公开内容放在 `zh`，私人草稿放在 `weiser`；不要只依赖 `status` 隔离私人内容。

## 自动导航与索引

根目录的 `docs/zh/.nav.yml` 只定义稳定的一级信息架构。栏目内部由 [Awesome Nav for MkDocs](https://lukasgeiter.github.io/mkdocs-awesome-nav/) 按文件结构生成，因此普通新增条目不再编辑站点配置。

`docs/zh/索引/index.md` 只保留一个生成标记。构建时，`tools/mkdocs_hooks.py` 会读取所有公开 Markdown，按栏目生成完整索引，并解析每页的 `related`。

## 主题与 SEO

“绯冠书库”主题使用 Telysta 的绯红作为交互主色，金色只作为封面礼仪色。亮色为暖纸面，暗色为暖灰黑；正文始终使用适合屏幕阅读的无衬线字体，衬线字体仅用于首页作品名。设计约定见 [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md)。

每个页面会生成 title、description、canonical、Open Graph、Twitter Card、JSON-LD 与面包屑结构化数据。CI 在构建后运行 `tools/validate_site.py`，检查本地链接和关键 SEO 元素。

## 多语言策略

中文是当前唯一正式且规范的内容版本。`docs/en/` 与 `mkdocs.en.yml` 保留英文骨架；只有当英文形成完整、可阅读的最小集合后，才加入部署并在中文站显示语言切换。日文目录目前仅为保留骨架，不参与线上发布。

## 部署

推送到 `main` 后，`.github/workflows/deploy.yml` 会锁定依赖、严格构建中文站、执行站点校验，并将 `site` 发布到 `gh-pages` 分支。自定义域名由 `docs/zh/CNAME` 与部署工作流共同保留。
