# 龙冠枯荣 / The Grand Annals

《龙冠枯荣》是以架空文明史、世界法则与人物命运为核心的中文幻想世界档案。本仓库同时作为 Obsidian 知识库与 MkDocs 网站源文件使用。

- 当前正式内容：简体中文
- 预留英文名：The Grand Annals
- 公开站点：<https://annals.telysta.com/>
- 网站源文件：`docs/zh/`
- 私人原始资料：`docs/weiser/`（不进入公开导航）

## 本地预览

```powershell
python -m pip install -r requirements.txt
python -m mkdocs serve --config-file mkdocs.yml
```

发布前使用严格模式检查导航与链接：

```powershell
python -m mkdocs build --strict --clean --config-file mkdocs.yml
```

## 内容架构

网站采用“封面 → 开始阅读 → 分类入口 → Wiki 条目”的四层结构：

- 首页只负责建立作品气质与提供两个明确入口。
- “开始阅读”为陌生读者提供一条三步阅读路径。
- 顶部导航展示稳定的世界分类，不默认展开全部树状目录。
- “条目索引”收录所有已经公开的条目；草稿不必为了填满目录而发布。
- 条目之间使用正文链接和人工维护的“相关条目”，暂不生成反向链接或知识图谱。

首页主入口采用零依赖的“暗金档案翻页”进入仪式。完整的产品目标、技术对比、交互时序与验收标准见 [`PRODUCT_DESIGN.md`](PRODUCT_DESIGN.md)。

## 新条目发布

1. 在 `docs/zh/` 的对应分类中创建 Markdown 文件。
2. 添加最少的 front matter：

   ```yaml
   ---
   title: 条目名称
   description: 一句话说明该条目对陌生读者的价值。
   type: character
   status: published
   tags:
     - 人物
     - 地域名称
   related:
     - 相关条目名称
   ---
   ```

3. 正文链接指向源 Markdown 文件，例如 `[长域](../山河地理/地理名词/长域.md)`，不要写 `docs/zh/...`。
4. 将已公开页面加入 `mkdocs.yml` 的对应导航，并加入 `docs/zh/索引/index.md`。
5. 执行严格构建，确认通过后再提交。

`tags`、`type`、`status` 和 `related` 目前属于编辑元数据，不会自动显示给读者。未来需要标签筛选时，再启用标签页面；不要为了展示标签而提前污染阅读界面。

## 多语言策略

`docs/en/` 与 `mkdocs.en.yml` 已保留英文版骨架，但当前 GitHub Actions 只发布中文主站，避免把占位页面暴露给公开读者。英文内容形成可阅读的最小集合后，再把英文构建加入部署流程并开启语言切换。

## 部署

推送到 `main` 后，[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) 会：

1. 安装锁定版本的依赖；
2. 以严格模式构建中文站点；
3. 将静态站点发布到 `gh-pages` 分支。

仓库的 GitHub Pages 发布来源保持为 `gh-pages` 分支。自定义域名由 `docs/zh/CNAME` 与部署工作流共同保留。
