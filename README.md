# 龙冠枯荣 / The Grand Annals

《龙冠枯荣》是以架空文明史、世界法则与人物命运为核心的中文幻想纪年项目。本仓库将内容创作与网站呈现分离：日常写作只在 `docs` 这座 Obsidian 库中进行，MkDocs 的 UI、SEO 与自动生成逻辑由仓库外层维护。

- 当前唯一正式版本：简体中文
- 正式英文名：The Grand Annals
- 公开站点：<https://annals.telysta.com/>
- 公开中文内容：`docs/zh/`
- 非站点原始资料：`docs/weiser/`（不会进入网站构建，但当前仍受公开 Git 仓库跟踪）
- 网站主题：`overrides/assets/`
- 内容自动化：`tools/mkdocs_hooks.py`

## 在 Obsidian 中写作

请把仓库中的 `docs` 文件夹单独作为 Obsidian 库打开，而不是打开整个仓库。

这个内容库已经配置：

- 新链接使用相对 Markdown 链接，移动文件时自动更新；
- `_templates` 提供通用、人物、地理、法则、历史与非发布草稿模板；
- `内容工作台.base` 汇总公开内容、缺少简介、缺少关联、非发布草稿和最近修改；
- 侧栏导航由独立目录配置维护，条目索引和文末相关条目自动生成；正文不需要写 UI HTML。

完整的新建流程见 Obsidian 库中的 `创作工作流.md`。

### 新建公开条目

1. 在 `docs/zh/` 的对应栏目中新建与条目同名的 Markdown 文件。
2. 在命令面板执行“模板：插入模板”，选择最接近的条目模板。
3. 填写 `description`，再开始写正文。
4. 为普通知识条目在 `related` 中精选 2～5 个前置、直接关系或延伸阅读，例如 `"[[长域]]"`；分类页不强制填写。
5. 执行严格构建。新条目会自动加入条目索引；重要条目成熟后再加入经过策划的侧栏导航。

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
.\.venv\Scripts\python.exe tools\validate_content.py
.\.venv\Scripts\python.exe -m mkdocs build --strict --clean --config-file mkdocs.yml
.\.venv\Scripts\python.exe tools\validate_site.py site
Start-Process .\.venv\Scripts\python.exe -ArgumentList "-m","http.server","8765","--directory","site"
.\.venv\Scripts\python.exe tools\validate_layout.py --base-url http://127.0.0.1:8765/
```

布局检查需要一个静态预览服务；检查结束后可在任务管理器或对应终端停止该 `http.server` 进程。平时使用 `mkdocs serve` 预览即可。

## 内容模型

公开页至少需要 `title` 与 `description`。网站发布边界由目录隔离：`docs/zh` 会发布，`docs/weiser` 不进入网站构建。栏目类型可由目录中的 `.meta.yml` 继承。

```yaml
---
title: 条目名称
description: 一句话说明该条目对陌生读者的价值。
type: 人物
aliases: []
tags:
  - 人物
related:
  - "[[相关条目]]"
---
```

- `tags` 是编辑与检索元数据，当前不在正文中展示。
- `aliases` 用于人物别名、译名与常见简称，并自动加入站内搜索词。
- `related` 会生成读者可见的文末关联卡片。
- `description` 同时用于索引说明、搜索摘要和 SEO。
- 公开内容放在 `zh`，不准备放上网站的草稿可放在 `weiser`；不要使用 `status` 字段，它是 MkDocs Material 的导航保留字段。
- 正文只写 Markdown，不写 HTML 或 `{: .class }` 网站样式标记。
- 段落或提示语之后开始列表时，先留一个空行再写 `- 条目`；Obsidian 与 MkDocs 使用的 Markdown 解析器并不完全相同，缺少空行会让 MkDocs 把短横线当作普通正文。

注意：本 GitHub 仓库当前是公开仓库，因此 `docs/weiser` 只能视作“网站不发布”，不能视作保密。真正私密的草稿应放入仓库之外的独立 Obsidian 库；如需让既有资料退出公开 Git 历史，应另行执行隐私迁移与历史清理。

## 导航与自动索引

`docs/zh/.nav.yml` 定义读者看到的精简信息架构，与作者的深层资料目录分离。普通新增条目无需立刻加入侧栏；当它成为主要入口或某一系列的成熟内容后，再把它加入该文件。这样可以防止地理归档路径直接泄漏为六七层导航。

`docs/zh/索引/index.md` 只保留一个生成标记。构建时，`tools/mkdocs_hooks.py` 会读取所有公开 Markdown，按栏目生成完整索引，并解析每页的 `related`。

## 主题与 SEO

“绯冠书库”主题使用 Telysta 的绯红作为交互主色，金色只作为封面礼仪色。亮色为暖纸面，暗色为暖灰黑；正文始终使用适合屏幕阅读的无衬线字体，衬线字体仅用于首页作品名。设计约定见 [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md)。

每个页面会生成 title、description、canonical、Open Graph、Twitter Card、JSON-LD 与面包屑结构化数据。CI 在构建后运行 `tools/validate_site.py`，检查本地链接和关键 SEO 元素。

## 多语言策略

中文是当前唯一正式且规范的内容版本。`docs/en/` 与 `mkdocs.en.yml` 保留英文骨架；只有当英文形成完整、可阅读的最小集合后，才加入部署并在中文站显示语言切换。日文目录目前仅为保留骨架，不参与线上发布。

## 部署

推送到 `main` 后，`.github/workflows/deploy.yml` 会锁定依赖、严格构建中文站、执行站点校验，并将 `site` 发布到 `gh-pages` 分支。自定义域名由 `docs/zh/CNAME` 与部署工作流共同保留。
