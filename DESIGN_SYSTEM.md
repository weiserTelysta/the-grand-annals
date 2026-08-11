# 绯冠书库：UI 设计系统

## 产品原则

网站首先是一座面向陌生读者的世界观 Wiki，其次才是作品展示页。

1. 首页建立气质，正文承担阅读；封面表现不进入条目页。
2. 绯红用于链接、选中、焦点和当前位置；金色只用于封面等礼仪性场景。
3. 正文、导航和组件使用无衬线字体；衬线字体只用于“龙冠枯荣”四字。
4. 组件依靠色面、间距和字重建立层级，避免厚边框、大阴影与过度卡片化。
5. 动效只说明状态变化，不模拟火焰、纸页或加载过程。

## 语义颜色

| 角色 | 亮色 | 暗色 | 用途 |
| --- | --- | --- | --- |
| Canvas | `#F8F4E8` | `#1D191A` | 页面底色 |
| Surface | `#FFFDF7` | `#252122` | 顶栏、搜索结果、浮层 |
| Surface Container | `#F1E9E1` | `#302B2C` | 搜索框、低强调组件 |
| Text | `#332A2A` | `#E9E0DC` | 正文 |
| Muted | `#6C6060` | `#B3A6A3` | 次要文字、目录 |
| Primary | `#8B2428` | `#E58A86` | 链接、焦点、当前项 |
| Primary Container | `#F7DEDC` | `#642225` | 选中与悬停色面 |
| Ceremonial | `#816718` | `#D6BC76` | 封面细节，不承担常规交互 |

正文、次要文字与主色在各自底色上均以 WCAG AA 为最低约束。不要直接在页面中写颜色值；所有组件应引用 `overrides/assets/stylesheets/tokens.css` 的语义变量。

## 字体与阅读宽度

- 正文：约 17px，行高 1.8，每行约 38 个汉字。
- H1：36–42px；H2：24–27px；H3：约 21px。
- 正文最高字重 600–650，避免大量粗黑文字争抢注意力。
- 作品名使用自托管的 Noto Serif SC 字形子集；正文使用系统无衬线字体栈。

## 组件

- 搜索框：静止时使用轻微容器色和底线，不出现强边框；聚焦时使用绯红描边与浅色焦点环。
- 引用：3px 绯红竖线、统一内边距；署名单独成段并右对齐。
- 提示框：全栏宽、低对比色面、左侧绯红状态线；正文不受阅读宽度二次限制。
- 相关条目：由 front matter 自动生成，默认两列，移动端一列。
- 页内目录：跟随阅读位置，当前项以绯红、字重和左侧标记共同表达。
- 首页入口：无矩形按钮；“开始阅读”的字号和字重高于“条目索引”，不使用箭头。

## 动效

| 场景 | 时长 | 表现 |
| --- | ---: | --- |
| 悬停与聚焦 | 140ms | 颜色、底线、轻微色面变化 |
| 条目进入 | 200ms | 透明度与 2px 位移 |
| 首页首次出现 | 220ms | 透明度与 4px 位移 |

所有动效使用标准链接并渐进增强；`prefers-reduced-motion: reduce` 时关闭。页面不得因动效延迟真实导航。

## 内容与呈现边界

- `docs` 只存 Markdown、内容图片、模板与编辑配置。
- `overrides` 存 Jinja 模板、CSS、JavaScript、主题字体。
- `tools` 存导航、索引、关联条目和验证逻辑。
- 正文不写按钮、卡片、导航等 UI HTML。

主要实现依据：[Material Design 3](https://m3.material.io/)、[Material for MkDocs 元数据继承](https://squidfunk.github.io/mkdocs-material/plugins/meta/)、[Awesome Nav](https://lukasgeiter.github.io/mkdocs-awesome-nav/)、[Obsidian Templates](https://obsidian.md/help/plugins/templates) 与 [Obsidian Bases](https://obsidian.md/help/bases/syntax)。
