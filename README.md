# YFSkillHub

我的私人 skillhub：每个 skill 独立成库，本仓库仅通过 git submodule 建立索引，不再保存 skill 内容。

| Skill | 本仓库目录 | 说明 | 仓库 |
|---|---|---|---|
| `translate-pdf` | `skill-translate-pdf` | 将 PDF 翻译为指定语言并生成结构化 PDF，尽量保留标题、段落、列表、公式和代码 | https://github.com/arnoliudaxia/skill-translate-pdf |
| `us-patent-download` | `skill-us-patent-download` | 使用 USPTO 官方端点下载美国已授权发明专利的 PDF，并校验下载结果 | https://github.com/arnoliudaxia/skill-us-patent-download |
| `feishu2md` | `skill-feishu2md` | 将飞书 / Lark 文档、文件夹或知识库导出为 Markdown | https://github.com/arnoliudaxia/skill-feishu2md |
| `p3d-model-extractor` | `skill-p3d-model-extractor` | 从 p3d.in 模型分享页提取 Draco/glTF 模型、PBR 纹理，生成 GLB 与 Blender 场景 | https://github.com/arnoliudaxia/skill-p3d-model-extractor |

## 使用

- 需要某个 skill 时，直接前往上表对应仓库获取，无需先克隆本仓库，也无需 `git clone --recurse-submodules`。
- 本仓库中的 4 个目录只是 submodule 指针，克隆后为空目录属正常。
- 如需一次性拉取全部内容：`git submodule update --init --recursive`。

## 约定

- git 来源的 skill 用 submodule 索引；npm 等非 git 来源的条目在仓库中建同名文件夹并放入 `SOURCE.md` 记录 URL，两者不并存。
