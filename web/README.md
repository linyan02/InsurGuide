# PC Web 前端模块

本目录为 PC Web 端静态资源与前端工程入口。

## 当前内容

- **static/index.html**：单页对话界面，调用后端 `POST /api/chat`，支持用户 ID、提问、展示答案与意图/溯源。

## 使用方式

1. 启动 API 服务：在项目根目录执行 `python main.py`（默认 http://localhost:8000）。
2. 浏览器访问：
   - 若 API 已挂载静态资源：http://localhost:8000/static/index.html
   - 或直接打开 `web/static/index.html`，在页面中填写 API 地址为 http://localhost:8000。

## 扩展

- 可在此目录下使用 Vue/React 等搭建完整 PC Web 工程，构建产物放入 `static/` 或由 Nginx 单独部署。
- 小程序端不在此目录，复用同一套 API（见 doc/项目说明.md）。
