前端说明

本项目的前端使用原生 HTML、CSS 和 JavaScript 编写，没有使用单独的 Node.js 构建工具。

源代码位置

app/templates/index.html
app/static/css/
app/static/js/

app/templates/index.html：页面结构；

app/static/css/：页面样式；

app/static/js/：登录、题目、提交、管理页面和 API 交互逻辑。

启动方式

前端由 FastAPI 后端直接提供，不需要执行独立的前端启动命令。

在项目根目录运行：

python -m uvicorn app.main:app --reload

然后访问：

http://127.0.0.1:8000/

主要页面功能

注册、登录与退出；

题目浏览与代码提交；

评测状态轮询和提交历史；

按角色显示评测日志；

教师和管理员查看完整评测日志及重新评测；

管理员进行用户管理；

管理员查看审计日志；

管理员创建、下载和恢复备份。

教师不能查看审计日志，审计日志仅向管理员开放。

技术说明

前端通过 fetch 调用 FastAPI API，并使用浏览器会话 Cookie 保持登录状态。页面会根据当前用户角色控制可见功能，但最终权限仍由后端 API 强制校验。