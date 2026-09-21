---
name: translate-pdf
description: Translate a text-extractable PDF into a structured PDF in the user's target language. Use for general documents such as reports, manuals, books, forms, contracts, presentations, and academic papers, while preserving headings, paragraphs, lists, formulas, code, citations, and other identifiable structure.
compatibility: Requires Python 3, Poppler pdftotext, and Chrome or Edge. The agent itself performs translation; no external translation API key is used.
---

# PDF 翻译工具

将 PDF 翻译为用户指定的目标语言并输出新的 PDF。默认目标语言为简体中文（除非用户另行指定）。采用**重排版（reflow）**：尽量保留文档的逻辑结构，而不是对原 PDF 逐字覆盖。不要修改或覆盖源 PDF。

## 核心约束

- **由当前 agent 自行翻译正文。不要调用翻译 Web/API 服务，不要要求或读取 `OPENAI_API_KEY`，也不要使用独立的 API 翻译脚本。**
- 除非用户明确要求双语版，否则只输出目标语言正文。
- 保留且不翻译（除非用户明确要求）：数学公式、LaTeX、代码、变量名、专有名词、缩写、数值、URL、DOI、文件名、命令和具有识别用途的编号。
- 对人名、机构名、产品名、标准名和技术术语，根据上下文决定保留原文或使用“译名（原文）”；同一文档中必须保持一致。
- 不要臆造 PDF 中不存在的内容、图、公式、表格或引用。无法可靠识别的内容应标注或说明，而不是猜测。
- 目标语言、术语风格和是否双语以用户要求为准；没有明确要求时使用自然、准确、正式的简体中文。

## 工作流

### 1. 找到并提取源文本

1. 确认用户提供的 PDF 路径；路径带 `@` 时去掉该前缀。
2. 创建临时工作目录，不在源 PDF 所在位置写入中间文件。
3. 使用 UTF-8 的 `pdftotext` 提取文本：

```bash
pdftotext -enc UTF-8 -raw "<source.pdf>" "<temp>/source.txt"
```

4. 检查提取结果是否有实际正文。若是扫描件、乱码、复杂排版或公式／表格提取严重损坏，明确说明限制，并请求用户允许 OCR 或接受文本重排结果；不要假装已可靠翻译不可提取的内容。

### 2. 识别并翻译结构

根据文档类型识别并尽量保留：

- 标题、副标题、作者、机构、日期、版本号和元数据；
- 章节、节、页眉页脚和编号层级；
- 正文段落、引文、定义、说明、警告和注释；
- 项目符号、编号列表、目录、步骤和表单字段；
- 图／表标题、图表中的可读文字、脚注、索引和附录；
- 参考文献、法规条款、术语表以及其他文档特有的末尾部分。

翻译正文时，不要把 PDF 换行当成句子边界；先合并断行和断词，再按语义段落翻译。表格、代码、公式、图表或特殊符号无法可靠提取时，应保留可识别的标题、编号和上下文，并在交付说明中列出限制。

### 3. 生成结构化 HTML

创建 UTF-8 HTML（临时目录或用户要求保留的可编辑文件），之后再转为 PDF。根据原文结构使用：

- `h1`、`h2`、`h3`：标题层级；
- `p`：正文；`blockquote`：引文；`ul`／`ol`：列表；
- `table`：可可靠重建的表格；`pre`／`code`：代码；
- 独立的 `section`：附录、参考文献、术语表等文档末尾部分，并在必要时从新页开始。

默认使用 A4 页面、约 18 mm 页边距、Noto Sans SC 或 Microsoft YaHei 中文字体、正文约 10–11 pt。用户指定其他语言时，选择该语言可读的字体。译文的页数不必与原文一致；优先保证内容完整、段落和标题关系正确。不要声称已逐像素复刻原始版式。

### 4. 输出 PDF

默认输出路径为源文件同目录下：

```text
<原文件名>_<目标语言代码>_翻译.pdf
```

调用本技能自带的渲染脚本：

```bash
python "<skill-dir>/scripts/render_pdf.py" \
  "<temp>/translated.html" "<output.pdf>"
```

也可按本技能目录的相对路径调用：`scripts/render_pdf.py`。

### 5. 完成检查与交付

- 确认输出 PDF 存在且大小大于零；不要覆盖源 PDF。
- 保留 HTML 仅在用户要求可编辑源文件时；否则清理临时目录。
- 最终回复给出输出 PDF 的绝对路径，简要说明：采用重排版、保留的结构、目标语言、双语／单语模式，以及扫描件、复杂表格、图片文字或特殊字体等任何实际限制。

## 不适用情形

本技能适合可提取文本的普通 PDF 文档。它不是出版级 PDF 编辑器：不能保证保留原始双栏坐标、复杂表格、字体、页码、图片或表单控件的精确位置。对扫描 PDF，先取得用户同意再进行 OCR；对包含敏感信息的文档，不要上传到外部服务。
