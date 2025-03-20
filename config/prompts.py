"""
提示语模板配置文件
包含所有用于 AI 模型的提示模板
"""

# 用于内容分析的提示
CONTENT_ANALYSIS_PROMPT = """
请对下面的内容进行分析，并返回格式化的 JSON，包含三个字段：

1. title: 内容的简洁标题（20 字以内）
2. summary: 内容的摘要概括（200-300 字）
3. tags: 3-5 个相关标签，优先从这些类别中选择：{categories}

只需返回 JSON，不要有其他文字。JSON 格式应该像这样：

{{
    "title": "标题",
    "summary": "摘要",
    "tags": ["标签 1", "标签 2", "标签 3"]
}}

内容如下：
{content}
"""

# PDF 分析提示（使用 Vision API）
PDF_ANALYSIS_PROMPT = """
你是一名专业的学术论文分析助手，你需要用英文思考，并用中文回答。{url_context}

请仔细阅读并分析论文内容，提供以下信息，使用 JSON 格式返回：

{{
  "title": "论文的完整标题",
  "brief_summary": "论文的简短摘要（200 字左右）",
  "insight": "论文的主要发现或贡献（100 字左右）",
  "details": "
        # 👀 核心问题
        - [待填充] 用一句话概括研究目标
        ## 现有方法不足： 
        - [列出 3 点]

        # 🧾 标题：
        “Scan through the section headings and subheadings to get an overview of the paper’s structure.”
        - 1. Section 1
        - 2. Section 2
        - 3. Section 3

        # 📐 方法论
        创新点流程图图解：（▢→▢→▢）
        ## 关键技术： 
        - [分点说明]
        ## 理论支撑： 
        - [定理名称]+[核心公式]

        # ⚗️ 实验验证
        ## 数据集特征： 
        - [数据量，领域差异]
        ## 指标对比： 
        - [表格形式呈现 FPR@95 等]
        ## 消融实验： 
        - [关键参数影响曲线]

        # 💠 启示与局限
        ## 可复现性： 
        - [代码/数据开放情况]
        ## 应用价值： 
        - [实际部署可能性]
        ## 改进方向： 
        - [作者讨论的未来工作]
        ## 创新点
        - [客观评价作者最具创新的工作，以及向外拓展的启发]
        
        # 📚 专业背景知识
        ## 相关领域的最核心的专业术语或概念
        - [列出 8-10 个英文、（缩写）、中文，并详细解释]
        ## 作者引用的前人工作
        - [列出 3-5 篇相关论文，并简要说明作者如何引用]"

}}

请务必使用以上准确的 JSON 格式返回结果，不要添加其他文字。
请确保 details 字段是一个字符串，内容使用 Markdown 格式，包含标题、列表等格式。
"""

# 新的 PDF 分析提示（使用 Vision API）
NEW_PDF_ANALYSIS_PROMPT = """
你是一名专业的学术论文分析助手，你需要用英文思考，并用中文回答。{url_context} 

请仔细阅读并分析论文内容，提供以下信息，使用 JSON 格式返回：

{{
  "title": "论文的完整标题",
  "brief_summary": "论文的简短摘要（200 字左右）",
  "insight": "论文的主要发现或贡献（100 字左右）",
  "details": "
## Skimming (Phase 1)

**Objective:** 
[To get a general understanding of the paper's structure, main ideas, and key sections.]

### 1. **👀Introduction and Conclusion:**
[Read the introduction and conclusion for context and summary of contributions.]
    * Introduction:
    * Conclusion:
### 2. **🧾Section Headings:**
[Scan through the section headings and subheadings to get an overview of the paper’s structure.]
    1.  Section 1
    2.  Section 2
    3.  Section 3
### 3. **📊Figures and Tables:**
[Look at figures, tables, and their captions to grasp the data and visual representations.]
### 4. **🔑Keywords:** 
### 5. **🧲IF:** 
### 6. **🧑Author Information:** 

---

## Detailed Reading (Phase 2)

**Objective:** 
[To thoroughly understand the paper’s methodology, results, and discussions.]

### 1. **📍Introduction:** 
[Read the introduction thoroughly to understand the background, problem statement, and objectives.]
### 2. **🧮Methods:** 
[Focus on the methods section to understand how the research was conducted.]
### 3. **📄Results:** 
[Study the results section for the findings of the study.]
### 4. **💬Discussion:** 
[Read the discussion to understand the implications of the results and how they relate to other work in the field.]
### 5. **🔍References:** 
[Look at the references to understand the paper’s grounding in existing literature.]
### 6. **🗂️Supplementary Materials:** 
[Review supplementary materials such as appendices or additional data sets for critical details.]
### 7. **🔖Re-read:** 
[Re-read complex or crucial sections to ensure full comprehension.]

---

## Critical Analysis (Phase 3)

**Objective:** 
[To critically evaluate the paper’s assumptions, methodologies, and conclusions.]

### 1.  **❗️Assumptions and Limitations:** 
[Identify the assumptions made in the study and any limitations acknowledged by the authors.]
    * Assumptions:
    * Limitations:
### 2.  **✔️
[Validity of Methods:** Evaluate the methods used for their validity and appropriateness.]
### 3.  **🔚Results:** 
[Critically analyze how the results are interpreted and whether the conclusions are justified.]
### 4.  **📡Broader Context:** 
[Consider the broader context and implications of the findings for the field.]
### 5.  **🧿Future Work:** 
[Look at suggestions for future work to see how this study could be expanded or improved.]
### 6.  **❓Bias:** 
[Identify any potential biases or contentious points that may affect the reliability and validity of the research.]
### 7.  **🪞Replicability:** 
[Consider whether the study is easily replicable and if the methods are detailed enough for other researchers to reproduce the results.]
### 8.  **💡Alternative Interpretations:** 
[Think about whether the results could be interpreted differently and if other methods might yield the same conclusions.]
## 📚 专业背景知识
### 相关领域的最核心的专业术语或概念
        - [列出 8-10 个英文、（缩写）、中文，并详细解释]
### 作者引用的前人工作
        - [列出 3-5 篇相关论文，并简要说明作者如何引用]
"
}}
请务必使用以上准确的 JSON 格式返回结果，不要添加其他文字，"[]"中的内容为对相应部分的解释和提示，在生成内容时，需要将这部分内容删除。确保输出为中文。请使用 Markdown 格式，确保正确使用以下语法：
                    - 使用 # 表示一级标题，## 表示二级标题 ### 表示三级标题
                    - 使用 **文本** 表示加粗文本
                    - 使用 *文本* 表示斜体文本
                    - 使用 - 表示列表项
                    - 使用表示引用
                    - 使用 [文本](链接) 表示超链接
"""

# PDF 文本分析提示（不使用 Vision API，仅文本）
PDF_TEXT_ANALYSIS_PROMPT = """
你是一名专业的学术论文分析助手。请分析下面从 PDF 中提取的文本内容。
由于是文本提取，可能会有格式问题，请尽力理解内容。

请提供以下信息，使用 JSON 格式返回：

{{
  "title": "论文的完整标题",
  "brief_summary": "论文的简短摘要（200 字左右）",
  "insight": "论文的主要发现或贡献（100 字左右）",
  "details": "
        # 👀 核心问题
        - [待填充] 用一句话概括研究目标
        ## 现有方法不足： 
        - [至少列出 3 点]

        # 🧾 标题：
        "Scan through the section headings and subheadings to get an overview of the paper’s structure."
        - 1. Section 1
        - 2. Section 2
        - 3. Section 3

        # 📐 方法论
        创新点流程图图解：（▢→▢→▢）
        ## 关键技术： 
        - [分点说明]
        ## 理论支撑： 
        - [定理名称]+[核心公式]

        # ⚗️ 实验验证
        ## 数据集特征： 
        - [数据量，领域差异]
        ## 指标对比： 
        - [表格形式呈现 FPR@95 等]
        ## 消融实验： 
        - [关键参数影响曲线]

        # 💠 启示与局限
        ## 可复现性： 
        - [代码/数据开放情况]
        ## 应用价值： 
        - [实际部署可能性]
        ## 改进方向： 
        - [作者讨论的未来工作]
        ## 创新点
        - [客观评价作者最具创新的工作，以及向外拓展的启发]
        
        # 📚 专业背景知识
        ## 相关领域的最核心的专业术语或概念
        - [列出 8-10 个英文、（缩写）、中文，并详细解释]
        ## 作者引用的前人工作
        - [列出 3-5 篇相关论文，并简要说明作者如何引用]

        请使用 Markdown 格式，确保正确使用以下语法：
                    - 使用 # 表示一级标题，## 表示二级标题 ### 表示三级标题
                    - 使用 **文本** 表示加粗文本
                    - 使用 *文本* 表示斜体文本
                    - 使用 - 表示列表项
                    - 使用表示引用
                    - 使用 [文本](链接) 表示超链接"
}}

请严格按照上述 JSON 格式返回结果，不要有任何其他文字，确保 details 字段是一个字符串而不是嵌套的对象。
PDF 内容如下：
{text}
"""
# 新的 PDF 文本分析提示（不使用 Vision API，仅文本）
NEW_PDF_TEXT_ANALYSIS_PROMPT = """
你是一名专业的学术论文分析助手。请分析下面从 PDF 中提取的文本内容。
由于是文本提取，可能会有格式问题，请尽力理解内容。

请提供以下信息，使用 JSON 格式返回：

{{
  "title": "论文的完整标题",
  "brief_summary": "论文的简短摘要（200 字左右）",
  "insight": "论文的主要发现或贡献（100 字左右）",
  "details": "
## Skimming (Phase 1)

**Objective:** 
[To get a general understanding of the paper's structure, main ideas, and key sections.]

### 1. **👀Introduction and Conclusion:**
[Read the introduction and conclusion for context and summary of contributions.]
    * Introduction:
    * Conclusion:
### 2. **🧾Section Headings:**
[Scan through the section headings and subheadings to get an overview of the paper’s structure.]
    1.  Section 1
    2.  Section 2
    3.  Section 3
### 3. **📊Figures and Tables:**
[Look at figures, tables, and their captions to grasp the data and visual representations.]
### 4. **🔑Keywords:** 
### 5. **🧲IF:** 
### 6. **🧑Author Information:** 

---

## Detailed Reading (Phase 2)

**Objective:** 
[To thoroughly understand the paper’s methodology, results, and discussions.]

### 1. **📍Introduction:** 
[Read the introduction thoroughly to understand the background, problem statement, and objectives.]
### 2. **🧮Methods:** 
[Focus on the methods section to understand how the research was conducted.]
### 3. **📄Results:** 
[Study the results section for the findings of the study.]
### 4. **💬Discussion:** 
[Read the discussion to understand the implications of the results and how they relate to other work in the field.]
### 5. **🔍References:** 
[Look at the references to understand the paper’s grounding in existing literature.]
### 6. **🗂️Supplementary Materials:** 
[Review supplementary materials such as appendices or additional data sets for critical details.]
### 7. **🔖Re-read:** 
[Re-read complex or crucial sections to ensure full comprehension.]

---

## Critical Analysis (Phase 3)

**Objective:** 
[To critically evaluate the paper’s assumptions, methodologies, and conclusions.]

### 1.  **❗️Assumptions and Limitations:** 
[Identify the assumptions made in the study and any limitations acknowledged by the authors.]
    * Assumptions:
    * Limitations:
### 2.  **✔️
[Validity of Methods:** Evaluate the methods used for their validity and appropriateness.]
### 3.  **🔚Results:** 
[Critically analyze how the results are interpreted and whether the conclusions are justified.]
### 4.  **📡Broader Context:** 
[Consider the broader context and implications of the findings for the field.]
### 5.  **🧿Future Work:** 
[Look at suggestions for future work to see how this study could be expanded or improved.]
### 6.  **❓Bias:** 
[Identify any potential biases or contentious points that may affect the reliability and validity of the research.]
### 7.  **🪞Replicability:** 
[Consider whether the study is easily replicable and if the methods are detailed enough for other researchers to reproduce the results.]
### 8.  **💡Alternative Interpretations:** 
[Think about whether the results could be interpreted differently and if other methods might yield the same conclusions.]
## 📚 专业背景知识
### 相关领域的最核心的专业术语或概念
        - [列出 8-10 个英文、（缩写）、中文，并详细解释]
### 作者引用的前人工作
        - [列出 3-5 篇相关论文，并简要说明作者如何引用]
"
}}

请严格按照上述 JSON 格式返回结果，不要有任何其他文字，确保 details 字段是一个字符串而不是嵌套的对象，请使用 Markdown 格式，确保正确使用以下语法：
                    - 使用 # 表示一级标题，## 表示二级标题 ### 表示三级标题
                    - 使用 **文本** 表示加粗文本
                    - 使用 *文本* 表示斜体文本
                    - 使用 - 表示列表项
                    - 使用表示引用
                    - 使用 [文本](链接) 表示超链接
确保输出为中文。
PDF 内容如下：
{text}
"""

# 更新后的周报提示
WEEKLY_SUMMARY_PROMPT = """
基于以下本周记录的内容，生成一份全面的周报总结。使用 Markdown 格式，包含以下部分：

1. 📊 **周统计**：对本周内容进行统计（条目总数、主要类别分布等）
2. 📌 **本周主题**：概括 2-4 个本周的整体主题或关注点
3. 📚 **内容分类与亮点**：将内容按主题分类（如学习、工作、阅读等）
4. 💡 **关键见解**：提取 3-5 个重要见解或想法
5. 🔄 **发展趋势**：分析本周内容与上周相比的变化趋势或新兴主题
6. 📝 **行动建议**：根据本周内容，提出 2-3 个下周可执行的具体行动建议

重要：对于引用的每一条内容，必须以这种格式引用：[引用的具体内容](ref:条目 ID)
例如：在"关键见解"部分，你可能会写"根据 [人工智能的快速发展需要更多伦理监管](ref:abc123def456)，我们应当..."

要求：
- 使用清晰简洁的语言
- 为每部分创建明确的标题，使用适当的 emoji
- 重点突出对知识积累和个人成长有价值的内容
- 每个要点必须引用至少一条原始内容，使用上述引用格式
- 提出实际可行的行动建议，帮助将积累的知识转化为实践
- 请提供完整且格式良好的周报，使用 Markdown 语法，以便于直接在 Notion 中显示

内容记录：
{entries_json}
"""
