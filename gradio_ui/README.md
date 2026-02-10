# Gradio 前端 UI 模块

采用**统一配置 + 页面模块化**架构，便于维护与扩展。

## 目录结构

```
gradio_ui/
├── __init__.py          # 对外暴露 build_demo
├── config.py            # 统一配置：从 config.settings / constants 读取 API 地址、路由、Logo、启动参数
├── app.py               # 主入口：组装页头 + 各 Tab，build_demo() / launch_demo()
├── components/          # 公共组件
│   ├── __init__.py
│   └── header.py        # 页头：Logo 位 + 应用标题（Logo 可配置或使用占位图）
├── pages/               # 各功能页（Tab），彼此独立
│   ├── __init__.py
│   ├── auth.py          # 用户认证（登录 / 注册）
│   ├── chat.py          # 对话服务（可选：自建增强 RAG / 直接对话大模型）
│   ├── vector.py        # 向量数据库检索（已从主界面移除，保留文件可复用）
│   ├── es.py            # Elasticsearch 搜索（已从主界面移除，保留文件可复用）
│   ├── rag.py           # 增强 RAG 逻辑（被 chat.py 复用）
│   └── ai_chat.py       # 直接对话 LLM 逻辑（被 chat.py 复用）
├── static/
│   └── logo_placeholder.png   # 默认 Logo 占位图（可替换为真实 Logo）
└── README.md
```

## 配置与路由

- **配置**：`config/settings.py` 中已增加  
  - `GRADIO_API_BASE_URL`：后端 API 根地址  
  - `GRADIO_LOGO_PATH`：首页 Logo 图片路径（空则使用 `static/logo_placeholder.png`）  
  - `GRADIO_PORT` / `GRADIO_SHARE`：启动参数  
- **路由**：`config/constants.py` 中定义 `GRADIO_ROUTE_*`，与后端路由一致；`gradio_ui/config.py` 中拼完整 URL 供各页面使用。

## 运行方式

在项目根目录执行：

```bash
python gradio_app.py
```

需先启动后端 API（`python main.py`），并安装依赖（含 `gradio`）。

## 扩展与修改

- **新增 Tab**：在 `pages/` 下新建模块，实现 `render()`，在 `app.py` 的 `build_demo()` 中 `with gr.Tabs():` 内增加一次 `render_xxx()` 调用即可。
- **更换 Logo**：在 `.env` 中设置 `GRADIO_LOGO_PATH=/path/to/your/logo.png`，或直接替换 `static/logo_placeholder.png`。
- **修改某页**：仅改对应 `pages/xxx.py`，不影响其他 Tab。
