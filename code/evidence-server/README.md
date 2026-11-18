# Exam Guardian 证据应用

证据服务使用 Django、Python、PyAV 和 MariaDB。学生在 Moodle 的同意面板开始采集，JavaScript 发送独立双轨 WebM。Django 按真实作答归档并按复核分配授权。分析任务在单独进程中运行，规则版本、观察、标记和人工意见留有记录。

## 先在本机跑通

需要 Python 3.12 或 3.13、支持 WebM 的普通浏览器和测试设备。从此目录执行。Windows PowerShell 用下面的命令。

```powershell
python -m venv .venv
$env:EG_DEBUG = '1'
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py setup_roles
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py fetch_face_model
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8090
```

在另一个终端用同一环境启动 `python manage.py evidence_worker --watch`。打开 [独立采集练习](http://127.0.0.1:8090/demo/)，同意后录制，暂停并等待服务器确认，随后交卷。登录 [证据工作台](http://127.0.0.1:8090/review/) 查看作答。管理员在「管理设置」新建账号，将账号加入「证据复核员」或「评审成员」，然后打开对应 Session 添加 Assignment。角色账号登录后只看到被分配的会话。管理员可在完成归档后安排 MediaPipe 或 OpenCV 分析。

如果本机 pip 配置把依赖重定向到全局目录，可在当前 PowerShell 窗口设置 `$env:PIP_CONFIG_FILE = 'NUL'` 后重新安装到虚拟环境。

本机数据库默认为 SQLite。短片文件默认在 `var/private`。`EG_DEBUG=1` 的运行方式用于回环测试。独立页只提供自建测试作答，其数据源显示为 `standalone`。

## 连接 Moodle

1. 先用 [现有演示说明](../lab/README.md) 跑通 Moodle、SEB Server、SEB。确认 Moodle 配置的 `cmid` 是课程活动编号，从对应 Quiz 取得真实 `quiz_id`。
2. 把 [自研插件](../lab/moodle-media) 的内容安装到 Moodle 的 `local/examguardianmedia`。按现有 Moodle 安装方式执行 `php admin/cli/upgrade.php --non-interactive`。在 Django Admin 创建 Exam，填写 `source_site`（与 `EG_MOODLE_SITE` 一致）、`cmid`、`quiz_id`、名称、考场标签，启用证据采集。
3. 用高强度随机值设置证据应用的 `EG_MOODLE_SECRET`。在 Moodle 自研插件配置 `evidencecmids`（允许长录的活动 ID，以逗号分隔）、`evidenceurl`（从 Moodle 服务端可达的 Django 地址）和 `evidencesecret`（同一凭证）。本机使用 Moodle 的 `admin/cli/cfg.php --component=local_examguardianmedia --name=配置项 --set=值`。只有旧版 `cmid` 配置的活动继续显示原型短录入口。证据应用配置 `EG_MOODLE_REVIEW_BASE` 后，复核页可链接到 Moodle 对应答卷。
4. 在 Moodle 站点仅转发 `/eg-ingest/` 到证据应用的同路径。Apache 可对该虚拟主机配置 `ProxyPass /eg-ingest/ http://127.0.0.1:8090/eg-ingest/`，需要 `proxy` 和 `proxy_http` 模块。Django 的 `/internal/moodle/` 从 Moodle 服务端单独访问。远端使用可信 HTTPS、固定域名、正确的上游 Host 与 Scheme 配置。
5. 让 Moodle 正常运行 cron。交卷及放弃的事件只在 Moodle 写入临时任务，任务通知证据应用关档。在测试站可执行 `php admin/cli/adhoc_task.php --classname='\local_examguardianmedia\task\finish_session'` 单独检查任务。证据 worker 完成收尾和分析。复核应用和 Moodle 各自登录。

## 部署配置

WSL Ubuntu 可安装 `python3-venv` 和数据库驱动的系统依赖 `pkg-config`、`default-libmysqlclient-dev`、`python3-dev`、`build-essential`，再使用 `requirements-deploy.txt`。为证据应用创建独立 MariaDB 库及最小权限账号，设置 `EG_DB_NAME`、`EG_DB_USER`、`EG_DB_PASSWORD`、`EG_DB_HOST`、`EG_DB_PORT`。配置 `EG_SECRET_KEY`、`EG_ALLOWED_HOSTS`、`EG_MEDIA_ROOT`。运行 `migrate`、`setup_roles`、`collectstatic --noinput` 后用 `gunicorn --bind 127.0.0.1:8090 exam_guardian.wsgi:application` 启动。

如果使用 Nginx，站点静态资源指向 `var/static`。证据回放可保留默认的 Django 单范围响应，或设 `EG_ACCEL_MEDIA=1`，并将 Nginx 的 `/_eg_private/` 配置为 `internal`、`alias` 指向私有媒体根目录。Nginx 正确覆盖 `X-Forwarded-Proto` 时可配置 `EG_TRUST_PROXY=1`。私有服务监听回环地址。配置 `EG_CSRF_TRUSTED_ORIGINS` 时只填教师端正确的 HTTPS 来源。通过未登录、未分配、正常分配和拖动回放四种测试验证部署。[Gunicorn 部署](https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/gunicorn/) · [Nginx internal](https://nginx.org/en/docs/http/ngx_http_core_module.html#internal)

`evidence_worker --watch` 每轮处理到期会话和待分析任务。记录默认在作答归档后保留 30 天，可按测试阶段调整。手动验证删除时在隔离数据库把会话到期时间设到过去，运行一次 `evidence_worker` 后检查旧回放链接与磁盘。团队原始素材、环境变量与私有目录留在受控实验环境。

## 复现检查

- 运行 `python manage.py fetch_face_model` 下载并校验 MediaPipe 和 OpenCV 的两个模型文件。接着运行 `python manage.py test` 检查身份、权限、双轨 WebM、重复上传、时序、Range、人工意见、分析和删除。
- `python -m playwright install chromium` 后运行 `python tools/browser_acceptance.py --disrupt --seconds 21`，检查设备模拟、断网、跨页、交卷、回放与复核。也可用 `--chromium` 指向本机 Edge。
- 在隔离的本机测试数据库运行 `python tools/browser_acceptance.py --pre-roll 15 --seconds 603`，记录整个会话和计时窗口各自的覆盖率、最大缺口及文件字节数。脚本在普通 Chromium 注入合成画面与音频，并创建测试账号。添加 `--native-fake` 可单独改用 Chromium 模拟设备。
- 在回环 Moodle 实验站用 `tools/moodle_fixture.php` 从现有测试题创建一份独立测验并生成本地测试账号。将该测验登记到 Django 后，通过 `tools/moodle_browser_acceptance.py` 核对身份、翻页、交卷和拒绝采集。
- 录制人工标注素材后，选择完成的 analysis job，将标签保存为 JSON。字段包括 `sessionId`、`events`（每条含 `kind`、`startMs`、`endMs`）和 `normalIntervals`（每项是起止毫秒）。运行 `python manage.py evaluate_evidence JOB_ID labels.json` 得到标记的精确率、召回率及正常片段误报数。标签类型可用 `NO_FACE`、`MULTIPLE_FACES` 和 `VOICE_ACTIVITY`。
- 物理设备验收在 Windows SEB 完成，记录摄像头、麦克风、显示器、实际许可提示、Moodle 状态和证据服务状态。标记后需能在授权页面按对应片段回放。

本项目的复核标记描述媒体里的可观察现象。考试是否合法及如何处理由有权限的人工流程决定。
