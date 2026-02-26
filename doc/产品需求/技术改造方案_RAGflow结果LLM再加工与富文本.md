# 技术改造方案：RAGflow 结果 LLM 再加工与富文本展示

> 本文档基于《RAGflow结果LLM再加工与富文本展示方案.md》产品方案，标注所有改动点，供开发实施参考。

---

## 一、改造概览

| 序号 | 改动文件 | 改动类型 | 改动摘要 |
|------|----------|----------|----------|
| 1 | `config/settings.py` | 新增 | 配置项 `ANSWER_USE_OPINION_FORMAT` |
| 2 | `app/answer_engine.py` | 修改 | 新增结构化 Prompt、模板选择逻辑 |
| 3 | `services/rag/langchain_chain.py` | 修改 | 替换/复用结构化 Prompt 模板 |
| 4 | `web/static/index.html` | 修改 | 统一 Markdown 渲染、样式、历史记录展示 |
| 5 | `gradio_ui/pages/chat.py` | 修改 | `rag_answer` 改为 Markdown 组件 |
| 6 | `.env.example`（可选） | 新增 | 新增配置项说明 |

---

## 二、改动点明细

---

### 【改动点 1】config/settings.py

**位置**：第 86 行之后（`USE_LANGCHAIN_RAG` 配置块之后）

**改动类型**：新增配置项

**改动内容**：

```python
# ---------- 增强 RAG 模式 ----------
USE_LANGCHAIN_RAG: bool = False

# 【新增】答案输出格式：True=结构化意见（Markdown），False=沿用旧版简洁模板
ANSWER_USE_OPINION_FORMAT: bool = True

# ---------- Gradio 演示页 ----------
```

**说明**：`ANSWER_USE_OPINION_FORMAT` 默认 `True`，启用结构化意见输出；设为 `False` 可回退到旧版 Prompt。

---

### 【改动点 2】app/answer_engine.py

#### 2.1 新增结构化 Prompt 模板（在 INSURANCE_PROMPT_TEMPLATE 之后）

**位置**：第 28 行之后（`INSURANCE_PROMPT_TEMPLATE` 定义结束的 `"""` 之后）

**改动类型**：新增常量

**改动内容**：

```python
"""


# 【新增】结构化意见 Prompt 模板（RAGflow 结果 LLM 再加工，输出 Markdown）
INSURANCE_OPINION_PROMPT_TEMPLATE = """
你是一位专业的保险顾问。请根据以下知识库内容，针对用户问题输出【结构化意见】。

## 输出要求（必须使用 Markdown 格式）：
1. **## 核心结论**：1-2 句简明回答，直接回应问题。
2. **## 详细说明**：分点展开（使用 - 或 1. 2. ），引用知识库关键信息，禁止编造。
3. **## 注意事项**：提醒用户需关注的风险点、除外情形或续保要求（如有）。
4. **合规声明**：结尾必须添加：本内容仅供参考，不构成投保建议，具体以保险合同条款为准。

## 格式规范：
- 使用标准 Markdown：标题用 ##、###，列表用 - 或数字，强调用 **加粗**
- 引用条款时用 > 引用块
- 语言简洁、专业，避免术语堆砌

## 知识库内容：
{knowledge_content}

## 历史上下文：
{context}

## 用户问题：
{query}

请直接输出结构化意见（Markdown），不要输出其他前缀或说明。
"""
```

#### 2.2 修改 generate_answer() 中的 Prompt 选择逻辑

**位置**：第 89-95 行

**原代码**：
```python
    knowledge_content = build_knowledge_content(ragflow_result)
    context_str = json.dumps(context, ensure_ascii=False) if context else "无"
    prompt = INSURANCE_PROMPT_TEMPLATE.format(
        knowledge_content=knowledge_content,
        context=context_str,
        query=query,
    )
```

**修改后**：
```python
    knowledge_content = build_knowledge_content(ragflow_result)
    context_str = json.dumps(context, ensure_ascii=False) if context else "无"
    # 根据配置选择 Prompt 模板：结构化意见 vs 旧版简洁模板
    template = (
        INSURANCE_OPINION_PROMPT_TEMPLATE
        if getattr(settings, "ANSWER_USE_OPINION_FORMAT", True)
        else INSURANCE_PROMPT_TEMPLATE
    )
    prompt = template.format(
        knowledge_content=knowledge_content,
        context=context_str,
        query=query,
    )
```

**说明**：通过 `getattr(settings, "ANSWER_USE_OPINION_FORMAT", True)` 兼容未升级 config 的旧环境，默认 True。

---

### 【改动点 3】services/rag/langchain_chain.py

#### 3.1 替换 INSURANCE_PROMPT_TEMPLATE 或按配置选择

**方案 A（推荐）**：从 answer_engine 导入模板，与配置保持一致

**位置**：第 27-41 行

**原代码**：
```python
# 与 app.answer_engine 保持一致，供 LangChain Prompt 使用
INSURANCE_PROMPT_TEMPLATE = """
基于以下知识库内容，结合用户历史对话上下文，回答用户问题，要求：
...
"""
```

**修改后**：
```python
# 与 app.answer_engine 保持一致，按配置选择模板
from app.answer_engine import (
    INSURANCE_PROMPT_TEMPLATE,
    INSURANCE_OPINION_PROMPT_TEMPLATE,
)

def _get_prompt_template():
    """根据配置返回使用的 Prompt 模板。"""
    use_opinion = getattr(settings, "ANSWER_USE_OPINION_FORMAT", True)
    return INSURANCE_OPINION_PROMPT_TEMPLATE if use_opinion else INSURANCE_PROMPT_TEMPLATE
```

#### 3.2 修改 run_chat_with_langchain 中的 Prompt 使用

**位置**：约第 152-157 行（PromptTemplate 与 chain.run 调用处）

**原代码**：
```python
    prompt = PromptTemplate(
        input_variables=["knowledge_content", "context", "query"],
        template=INSURANCE_PROMPT_TEMPLATE,
    )
```

**修改后**：
```python
    prompt = PromptTemplate(
        input_variables=["knowledge_content", "context", "query"],
        template=_get_prompt_template(),
    )
```

**说明**：保证 LangChain 模式与 pipeline 模式输出格式一致。

---

### 【改动点 4】web/static/index.html

#### 4.1 新增 renderAnswer() 函数（统一 Markdown 渲染）

**位置**：第 398-400 行之间（`nl2br` 函数之后，`document.getElementById('btn-send')` 之前）

**改动类型**：新增函数

**改动内容**：

```javascript
            function nl2br(s) {
                return escapeHtml(s || '').replace(/\n/g, '<br>');
            }

            /**
             * 统一将答案渲染为富文本：优先 Markdown，异常时降级为 nl2br。
             * 用于实时回复与历史记录恢复。
             */
            function renderAnswer(rawAnswer) {
                if (!rawAnswer || !String(rawAnswer).trim()) return '';
                const text = String(rawAnswer).trim();
                if (typeof marked === 'undefined') {
                    return nl2br(text);
                }
                try {
                    marked.setOptions({ breaks: true });
                    let html = marked.parse(text);
                    html = html.replace(/<blockquote>/g, '<blockquote class="case-card">');
                    return html;
                } catch (e) {
                    return nl2br(text);
                }
            }

            document.getElementById('btn-send').addEventListener('click', handleSend);
```

#### 4.2 修改 handleSend 中的答案渲染逻辑

**位置**：第 451-464 行

**原代码**：
```javascript
                        let rawAnswer = d.answer || '';
                        let html;
                        if (typeof marked !== 'undefined' && (rawAnswer.includes('![') || rawAnswer.includes('> **相似案例**') || rawAnswer.includes('\n> '))) {
                            try {
                                marked.setOptions({ breaks: true });
                                html = marked.parse(rawAnswer);
                                html = html.replace(/<blockquote>/g, '<blockquote class="case-card">');
                            } catch (_) {
                                html = nl2br(rawAnswer);
                            }
                        } else {
                            html = nl2br(rawAnswer);
                        }
```

**修改后**：
```javascript
                        let rawAnswer = d.answer || '';
                        let html = renderAnswer(rawAnswer);
```

#### 4.3 修改历史记录恢复时的 AI 答案渲染

**位置**：第 352-354 行

**原代码**：
```javascript
                            var aiHtml = '<div class="w-full max-w-3xl flex gap-4 animate-slide-up chat-msg">' +
                                '<div class="w-10 h-10 bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-300 rounded-full flex items-center justify-center font-bold shadow-sm shrink-0">灵</div>' +
                                '<div class="bg-white dark:bg-gray-800 border dark:border-gray-600 p-6 rounded-3xl rounded-tl-none shadow-sm text-gray-800 dark:text-gray-200 leading-relaxed">' + nl2br(d.answer || '') + '</div></div>';
```

**修改后**：
```javascript
                            var aiHtml = '<div class="w-full max-w-3xl flex gap-4 animate-slide-up chat-msg">' +
                                '<div class="w-10 h-10 bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-300 rounded-full flex items-center justify-center font-bold shadow-sm shrink-0">灵</div>' +
                                '<div class="bg-white dark:bg-gray-800 border dark:border-gray-600 p-6 rounded-3xl rounded-tl-none shadow-sm text-gray-800 dark:text-gray-200 leading-relaxed ai-answer-content">' + renderAnswer(d.answer || '') + '</div></div>';
```

**说明**：历史记录中的 answer 也统一使用 `renderAnswer`，并增加 `ai-answer-content` 以应用富文本样式。

#### 4.4 富文本样式增强（可选，建议实施）

**位置**：第 30-34 行（style 区块内）

**原代码**：
```css
        .case-card { background: #eef6fc; border-left: 4px solid #1a73e8; border-radius: 12px; padding: 1rem 1.25rem; margin: 0.75rem 0; }
        .dark-mode .case-card { background: #1e3a5f; border-left-color: #60a5fa; }
        .ai-answer-content img { max-width: 100%; border-radius: 8px; margin: 0.5rem 0; }
        .ai-answer-content blockquote { border-left: 4px solid #1a73e8; padding-left: 1rem; margin: 0.5rem 0; color: #374151; }
```

**修改后**：
```css
        .case-card { background: #eef6fc; border-left: 4px solid #1a73e8; border-radius: 12px; padding: 1rem 1.25rem; margin: 0.75rem 0; }
        .dark-mode .case-card { background: #1e3a5f; border-left-color: #60a5fa; }
        .ai-answer-content img { max-width: 100%; border-radius: 8px; margin: 0.5rem 0; }
        .ai-answer-content blockquote { border-left: 4px solid #1a73e8; padding-left: 1rem; margin: 0.5rem 0; color: #374151; }
        /* 富文本：标题、列表、表格 */
        .ai-answer-content h2 { font-size: 1.125rem; font-weight: 600; margin: 1rem 0 0.5rem; color: #1f2937; }
        .ai-answer-content h3 { font-size: 1rem; font-weight: 600; margin: 0.75rem 0 0.375rem; color: #374151; }
        .ai-answer-content ul, .ai-answer-content ol { margin: 0.5rem 0; padding-left: 1.5rem; }
        .ai-answer-content li { margin: 0.25rem 0; }
        .ai-answer-content table { border-collapse: collapse; width: 100%; margin: 0.75rem 0; font-size: 0.875rem; }
        .ai-answer-content th, .ai-answer-content td { border: 1px solid #e5e7eb; padding: 0.5rem 0.75rem; text-align: left; }
        .ai-answer-content th { background: #f3f4f6; font-weight: 600; }
        .ai-answer-content tr:nth-child(even) { background: #f9fafb; }
        .dark-mode .ai-answer-content h2, .dark-mode .ai-answer-content h3 { color: #e5e7eb; }
        .dark-mode .ai-answer-content th, .dark-mode .ai-answer-content td { border-color: #374151; }
        .dark-mode .ai-answer-content th { background: #374151; }
        .dark-mode .ai-answer-content tr:nth-child(even) { background: #1f2937; }
```

---

### 【改动点 5】gradio_ui/pages/chat.py

#### 5.1 将 rag_answer 从 Textbox 改为 Markdown

**位置**：第 118 行

**原代码**：
```python
            rag_answer = gr.Textbox(label="答案", lines=8)
```

**修改后**：
```python
            rag_answer = gr.Markdown(label="答案")
```

**说明**：Gradio 的 `gr.Markdown` 会直接渲染 Markdown 富文本，与 Web 端表现一致。若需固定高度可在外层包 `gr.Column` 并设置 `height`。

---

## 三、改动依赖关系

```
config/settings.py (1)
        │
        ▼
app/answer_engine.py (2) ◄──── services/rag/langchain_chain.py (3)
        │
        └──► API 返回 answer (Markdown)
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
web/static/index.html (4)   gradio_ui/pages/chat.py (5)
```

- **1 → 2**：`answer_engine` 读取 `ANSWER_USE_OPINION_FORMAT`
- **2 → 3**：`langchain_chain` 从 `answer_engine` 导入模板
- **2** 不依赖 4、5，前端可独立改造后联调

---

## 四、实施顺序建议

1. **config/settings.py**：新增配置项
2. **app/answer_engine.py**：新增模板与选择逻辑
3. **services/rag/langchain_chain.py**：导入模板并按配置使用
4. **web/static/index.html**：新增 `renderAnswer`、修改 handleSend 与历史记录、样式
5. **gradio_ui/pages/chat.py**：Textbox 改为 Markdown
6. 联调验证：提问 → 检查结构化输出 → 检查富文本展示

---

## 五、回归检查清单

| 检查项 | 预期 |
|--------|------|
| 配置 `ANSWER_USE_OPINION_FORMAT=True` | 答案含「核心结论」「详细说明」「注意事项」等结构 |
| 配置 `ANSWER_USE_OPINION_FORMAT=False` | 答案为旧版简洁格式 |
| Web 实时回复 | 标题、列表、引用块正确渲染 |
| Web 历史记录恢复 | 与实时回复展示一致 |
| Gradio 答案区 | Markdown 正确渲染 |
| 合规声明 | 结尾仍有标准 disclaimer |
| 违规词屏蔽 | 仍生效 |
| 图片/案例 | `enrich_answer_with_rich_content` 仍追加到答案末尾 |

---

## 六、附录：完整改动文件清单

| 文件路径 | 改动行数（约） | 改动说明 |
|----------|----------------|----------|
| `config/settings.py` | +3 | 新增 `ANSWER_USE_OPINION_FORMAT` |
| `app/answer_engine.py` | +35, 修改 8 | 新增模板、修改 `generate_answer` |
| `services/rag/langchain_chain.py` | +10, 修改 6 | 导入模板、`_get_prompt_template`、修改 PromptTemplate |
| `web/static/index.html` | +25, 修改 15 | `renderAnswer`、handleSend、历史记录、样式 |
| `gradio_ui/pages/chat.py` | 修改 1 | Textbox → Markdown |

---

*文档版本：v1.0*
*对应产品方案：RAGflow结果LLM再加工与富文本展示方案.md*
*最后更新：2025-02-25*
