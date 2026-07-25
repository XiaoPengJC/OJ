FastAPI 在线评测系统

本项目是一个使用 Python、FastAPI、SQLite 以及原生 HTML、CSS 和 JavaScript 构建的在线评测系统。系统实现了用户认证、角色权限、题目管理、代码提交、自动评测、评测日志、重新评测、审计日志以及数据库备份与恢复等功能。

1. 环境要求

Python 3.10 或以上版本

支持启动 Python 子进程的桌面操作系统

推荐使用 macOS、Linux 或 Windows

2. 项目结构

oj_project/
├── app/
│   ├── judge/              # 代码运行、输出比较与评测逻辑
│   ├── models/             # 数据模型
│   ├── repositories/       # SQLite 数据访问
│   ├── routers/            # FastAPI 路由
│   ├── services/           # 业务逻辑
│   ├── static/             # CSS 与 JavaScript
│   ├── templates/          # HTML 页面
│   ├── utils/              # 权限、日志和通用工具
│   ├── config.py
│   └── main.py
├── data/                   # 运行时数据库与备份目录
├── frontend/
│   └── README.md           # 前端位置说明
├── report/
│   └── report.md           # 项目报告
├── temp/                   # 学生程序临时运行目录
├── tests/                  # pytest 自动化测试
├── .gitignore
├── README.md
├── requirements.txt
└── seed_demo_problems.py   # 可选演示题目初始化脚本

3. 安装依赖

在项目根目录执行：

python -m venv .venv

macOS 或 Linux：

source .venv/bin/activate

Windows PowerShell：

.venv\Scripts\Activate.ps1

安装依赖：

python -m pip install -r requirements.txt

4. 启动系统

在项目根目录运行：

python -m uvicorn app.main:app --reload

然后在浏览器中打开：

http://127.0.0.1:8000/

FastAPI 自动生成的接口文档位于：

http://127.0.0.1:8000/docs

5. 初始管理员账号

系统首次启动时，如果数据库中尚不存在管理员账号，会自动创建以下本地演示账号：

用户名：admin

密码：admin12345

该账号仅用于课程验收和本地演示，不应作为真实生产环境账号。可以通过环境变量覆盖默认值：

export OJ_ADMIN_USERNAME="admin"
export OJ_ADMIN_PASSWORD="your-own-password"

Windows PowerShell：

$env:OJ_ADMIN_USERNAME="admin"
$env:OJ_ADMIN_PASSWORD="your-own-password"

密码在写入数据库前会进行哈希处理，数据库中不直接保存明文密码。

6. 可选环境变量

环境变量

作用

OJ_PROJECT_ROOT

项目根目录

OJ_DATABASE_PATH

SQLite 数据库文件路径

OJ_BACKUP_DIR

备份目录

OJ_TEMP_DIR

学生程序临时运行目录

OJ_SESSION_SECRET

会话签名密钥

OJ_ADMIN_USERNAME

首次启动时创建的管理员用户名

OJ_ADMIN_PASSWORD

首次启动时创建的管理员密码

未设置时，系统使用项目内置的本地演示配置。

7. 前端说明

前端使用原生 HTML、CSS 和 JavaScript 编写，源代码位于：

app/templates/index.html
app/static/css/
app/static/js/

前端由 FastAPI 直接提供，因此不需要单独安装 Node.js，也不需要运行独立的前端开发服务器。

主要功能包括：

学生注册、登录和退出；

浏览题目并提交 Python 代码；

自动轮询评测状态并查看提交历史；

根据用户角色显示不同粒度的评测日志；

教师和管理员查看完整评测日志并重新评测；

管理员管理用户、查看审计日志以及执行备份和恢复。

其中，审计日志仅允许管理员查看。

8. 自动化测试

在项目根目录运行：

python -m pytest -v

最终验收版本的测试结果为：

15 passed, 1 warning in 6.75s

测试覆盖的主要内容包括：

注册、登录和角色权限；

题目创建、查询、修改与删除；

AC、WA、RE、TLE 等评测结果；

隐藏测试点日志脱敏；

提交状态变化与重新评测；

数据持久化；

备份创建、校验与恢复。

9. 数据持久化

系统使用 SQLite 保存数据，默认数据库路径为：

data/oj.db

如果数据库文件不存在，系统会在启动时自动创建所需表结构，并创建初始管理员账号。

运行时数据库属于可重新生成的数据，正式提交和 Git 仓库中通常不包含该文件。

10. 备份与恢复

备份文件默认保存在：

data/backups/

每个备份 ZIP 包包含：

oj.db

manifest.json

恢复前，系统会检查备份结构和清单信息。恢复成功后，当前浏览器会话会失效，需要重新登录。

正式提交中不包含运行过程中生成的备份文件，只保留空的备份目录。

11. 主要 API

认证：/api/auth/*

题目：/api/problems

提交：/api/submissions

单次提交日志：/api/submissions/{submission_id}/logs

教师与管理员评测日志：/api/logs

用户管理：/api/users

审计日志：/api/audit-logs

备份与恢复：/api/admin/backups

具体参数、权限和响应格式见：

report/report.md

或启动系统后访问：

/docs

12. 安全边界与已知限制

学生代码在独立临时目录和独立子进程中运行，并设置时间限制、输出长度限制以及最小化环境变量。

当前实现满足课程基础模块要求，但不是生产级沙箱，仍存在以下限制：

未使用 Docker 或其他容器隔离；

未实现完整网络隔离；

未实现严格的文件系统隔离；

未实现操作系统级内存限制；

仅支持 Python 程序评测；

未实现特殊评测、严格比较器或代码相似度检测。

因此，本项目仅适用于可信的本地课程演示环境。

13. Git 提交规范

项目使用 Conventional Commits 风格，例如：

feat: add submission rejudge
fix: prevent hidden test data exposure
test: add backup restore tests
docs: finalize report and readme
chore: clean submission files

以下内容不应提交到 Git：

.venv/ 或 venv/

__pycache__/、.pyc 和 .pytest_cache/

tests/.runtime/

temp/ 中的运行时文件

data/oj.db

data/backups/ 中生成的备份

.DS_Store、._* 和 __MACOSX/

重复源码目录或临时备份目录

14. 项目仓库

GitHub 仓库：

https://github.com/XiaoPengJC/OJ