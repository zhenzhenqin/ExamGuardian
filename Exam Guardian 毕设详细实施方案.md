# Exam Guardian 毕业设计实施方案

2026 年 11 月 16 日 · 基于开题报告 v2、11 月 13 日周会及 11 月 15 日实施计划

建议保留现有 **Windows SEB + Moodle + SEB Server** 考试环境，优先验证 **Python + Django** 作为独立证据与复核应用。Moodle 插件在获准的答题页面加载采集界面，并确认录制属于谁的哪一次答题。JavaScript 采集音视频，Django 保存文件、管理权限和提供回放，Python 分析任务在考试结束后取得人脸数量和语音活动结果。教师点一条标记，就能查看对应时间附近的原始证据，并留下复核意见。

## 1. 现有进度和交付范围

| 工作 | 文件中的证据 | 下一项验收 |
| --- | --- | --- |
| 考试链路 | 实机记录为 Moodle 4.5.15+、SEB Server 2.2、官方 Moodle 插件 2.1、Windows SEB 3.10.2。SEB 内完成两题，Moodle 显示 `Finished`、10/10 | 复制一份测验，关闭自研采集，补一条可复现的 E1 基线记录 |
| 音视频采集 | 作答页取得摄像头和麦克风，已有约 2.7 秒的 `EG-1`，关联活动 `cmid=6`、作答 `attemptId=3` | 第二人跑通。然后测 60 秒及连续 10 分钟的双轨接收、回放和导航中断 |
| 证据与权限 | 原型保存 WebM、设备时间、接收时间、考场标签及 SHA-256。教师可按作答回放，已记录一项学生被拒绝的测试 | 独立证据服务、四类角色、分配权限、回放时间轴、复核与删除 |
| SEB Server 监控 | 教师跳转已通。后台有 `ACTIVE` 到 `CLOSED` 的记录，页面学生计数仍为 0 | 用两个独立登录上下文在作答进行中复测，记下考试 ID、时间与结果。到演示期限仍异常时，使用已验证的 Moodle 证据页回查 |
| 分析与论文 | 已定义人脸与语音的研究问题，当前工作区材料尚无已验证的分析结果 | 同批素材比较工具和阈值，交付可复算的结果表与典型错误 |

实现以 [新版开题稿](v2/Exam_Guardian_Project_Proposal_v2.md) 及同名 v2 Word 为依据。[已有实施计划](Exam%20Guardian%20毕设后续实施计划.md) 有实机进度和近期交付，[演示记录](code/lab/README.md) 有启动与测试证据。[需求对照](v2/修改汇总与需求对照.md) 记录导师反馈与版本调整。`v2` 下的 `Exam_Guardian_Project_Proposal_final.docx` 仍有旧文案，v1 的 18 页 PPT 和讲稿也沿用旧范围及示例数字。后续对外材料采用 v2 的研究问题和真实测试结果。实机结果引用现有记录，拟建证据应用、长录和分析仍需验收。

最终可演示的场景是学生录制和交卷、管理员分配复核、复核员按时间定位原片并给出意见、评审成员查看并评论。基本检测为画面人脸数量与语音活动，附可配置的优先级。先保证这一流程可跑完，再考虑头部姿态、可见物体、说话人区分、转写和实时提示。采集故障或检测标记出现时，答题和交卷照常；复核结果保留在证据应用。

## 2. 系统怎么连接

```text
Windows SEB ── 答题与交卷 ──→ Moodle Quiz
Windows SEB ←── 启动配置 ──── SEB Server ←── 官方插件 ──→ Moodle

Moodle 自有插件 ── 确认作答归属 ──→ Django 证据应用
作答页采集脚本 ──── 上传音视频 ────→ Django 证据应用
                                      ├─ MariaDB：会话、时间、权限、意见
                                      ├─ 私有目录：音视频证据
                                      ├─ Python：离线人脸、语音分析
                                      └─ 教师浏览器：时间轴、回放、复核
```

| 组件 | 职责和技术 |
| --- | --- |
| 学生考试 | 沿用 Windows SEB 3.10.2、Moodle 4.5.15+ 的 Quiz 和内置 SEB 访问规则。Moodle 保存题目、答卷、交卷状态、成绩 |
| 考试编排 | 沿用 SEB Server 2.2 和 `quizaccess_sebserver` 2.1。通过 Assessment Tool Setup 连接 Moodle，提供模板、启动配置、导入和教师监控 |
| 采集接入 | 自有 Moodle `local_examguardianmedia` 插件，PHP 只做页面 Hook、登录校验、作答身份确认及生命周期通知。原生 JavaScript 使用 `getUserMedia`、`MediaRecorder`、`fetch`，翻页增强使用 IndexedDB |
| AP Server / 证据应用 | Python 3.11 + Django 5.2 LTS。使用内置账号、组、会话、ORM 和迁移，单个 Django 项目管理作答会话、证据和复核。按 `review_assignment` 补充逐会话权限 |
| 界面 | Django 模板、HTML/CSS、少量 JavaScript 和浏览器 `<video>`。管理员表单先用 Django Admin，复核员和评审使用面向任务的列表、时间轴和意见页。学生状态在 Moodle 作答页显示 |
| 数据和文件 | Django MySQL 后端 + `mysqlclient` + 独立 MariaDB 库和账号。开发练习可用 SQLite，集成验收用 MariaDB。媒体放在私有目录，FFprobe 检查轨道、编码和时长，FFmpeg 用于音频转换和必要的回放修复 |
| Model Server / 分析模块 | Python 虚拟环境中运行 MediaPipe Face Detector、OpenCV Haar 对照、FFmpeg 和 WebRTC VAD。分析做独立命令行进程，按约定的 JSON 输出结果，可和 Django 部署在同一台机器 |
| 传输验证与部署 | aiortc 官方示例用于 WebRTC 实验。Windows + WSL Ubuntu，沿用 Apache Moodle 和 Docker SEB Server，Django 通过 Gunicorn 运行。联机阶段用 Nginx HTTPS 入口和鉴权后的回放转发 |

版本以团队机器实测为准。依赖在首次兼容试验后锁定。模型文件记录来源、许可证和校验值。项目代码、配置样例、复现步骤和脱敏实验表进入私有仓库。[Django 认证](https://docs.djangoproject.com/en/5.2/topics/auth/default/) · [Django 数据库支持](https://docs.djangoproject.com/en/5.2/ref/databases/) · [FFprobe 文档](https://ffmpeg.org/ffprobe.html)

### 为什么优先验证 Django

主要工作包含管理员录入、登录、角色分配、文件上传、复核界面和数据库修改历史。Django 自带账号、管理后台、页面模板和数据库迁移，能用较少组件覆盖这些功能。分析脚本也用 Python，Web 业务与分析仍可以独立运行和排错。FastAPI 适合以 API 为主的路线，当前四类用户和复核界面需要配套实现账号数据、数据库迁移和管理页面。Spring Boot 加 Python 同样可行，适合团队能借助现成 Spring 工程更快完成权限、页面和媒体回放的情形。个人会 Java 是分工和上手的条件，团队的实际交付成本才是框架判断依据。[Django Admin](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/) · [FastAPI 功能](https://fastapi.tiangolo.com/features/)

以一个小实验确认选择。用同一段测试 WebM 完成「上传到一个作答 → 登录并分配复核员 → 授权播放 → 未分配账号拒绝 → 导入一条分析 JSON」。记录部署步骤、实际耗时和卡点。现有 Moodle 短片演示可以同时继续。证据框架和媒体传输分别验证，WebRTC 实验结果只影响传输选型。

### 官方文档如何对应你们的版本

1. Moodle 文档的 **Safe Exam Browser** 是每个 Quiz 的访问设置。手动配置、上传 `.seb`、使用客户端配置适合不同基线。需要人工使用 Browser Exam Key 时，按文档从 Moodle 下载最终配置，再用对应版本的 SEB 取得 Key。Moodle 会改写某些上传配置，最终下载文件才是验证依据。[Moodle 4.5 文档](https://docs.moodle.org/405/en/Safe_Exam_Browser)
2. 你给的 **5.3** 文档里，最大显示器数等项新增到了手动配置界面。当前实验环境继续按 4.5 的实际界面和已经验证的 SEB Server 考试模板操作，记录摄像头、麦克风、显示器和退出设置。材料中记录的双显示器是该演示配置的实测条件。[Moodle 5.3 文档](https://docs.moodle.org/503/en/Safe_Exam_Browser)
3. 官方 SEB Server 集成插件安装到 Moodle 的 `mod/quiz/accessrule/sebserver`。启用 Moodle REST Web Services，给专用 API 账户配置插件服务及所需权限。按已安装插件的 README 配置服务上传下载和令牌，移动服务按所选集成模式的需要启用。在 SEB Server 绑定 Moodle，一套 Moodle 对应一个已绑定的 SEB Server。创建标记为 **Assessment Tool Integration** 的模板，给它关联允许摄像头和麦克风的考试配置。在测试 Quiz 启用 **Enable SEB Server** 并选模板，保存后核对自动导入、考试运行时间、学生启动配置和教师入口。按你们当前的 2.1 版本界面核对叫法。[SEB Server Moodle 集成](https://seb-server.readthedocs.io/en/latest/lms_moodle.html) · [官方插件安装和 API 账户配置](https://github.com/ethz-let/moodle-quizaccess_sebserver)
4. 自有插件用 `local/examguardianmedia`。`classes/attempt_panel.php` 已利用 Moodle Hook 加载 `attempt-media.js`，`upload.php` 和 `clip.php` 已验证原型上传和回放。把它作为后续采集入口，继续利用 Moodle 的作答实体和权限判断，官方组件依旧按现有安装的接口运行。[自有插件源码](code/lab/moodle-media) · [Moodle 4.5 Hook API](https://moodledev.io/docs/4.5/apis/core/hooks)

## 3. 先选择能验收的传输路线

| 验证路线 | 怎么做 | 通过依据 |
| --- | --- | --- |
| 主开发路线：MediaRecorder + HTTP 上传 | 复用当前脚本，在固定时间窗结束一个 `MediaRecorder`、生成完整 WebM 并上传。下一段复用已获准的音视频流重新录制 | 同一作答连续 10 分钟，双轨可回放，段序正确，有覆盖和缺口记录。补翻页、断网、重连、交卷实验 |
| E3：WebRTC 接收 | 运行 aiortc 官方接收示例，先在 Edge 录 60 秒，再在 SEB 录 60 秒，稳定后录 10 分钟。检查示例是否保存两条输入轨、收尾文件是否完整 | 比较首段到达和可播放延迟、双轨、断流与重连、CPU、磁盘、部署时间。安排两轮验证，记录结果并在 M2 决定是否替换录制接收路线 |
| E4：独立采集页 | 复用 `media-test.html`。普通浏览器先跑，再在 SEB 获准页面测试。独立演示可由证据应用创建测试作答会话 | 普通浏览器仍可验收证据链。使用自建作答 ID 的结果标明其来源。SEB 兼容和 Moodle 真实作答关联各自报告 |
| E4：代理嵌入方案评估 | 对照评估经证据服务代理 Moodle 考试页面需要处理的登录、URL 和维护工作量，记录其对答题路径的影响 | E4 报告给出取舍依据。部署同源上传时的路径转发只转发证据请求，与这个实验方案原理不同 |

主路线先以 320×180、15 fps、约 5–10 秒一段作为试验起点。不要把 `recorder.start(1000)` 回调的每个 `Blob` 当作独立 WebM，因为同一次录制拆出的 Blob 可能依赖其他 Blob 才能播放。用 `stop` 后生成的完整文件先验证，测量重复启动的段间间隔；如果间隔破坏连续性门槛，再试同一个录制实例按序上传，服务端按实例保存全部分块并在录制结束后组装、校验和索引，或采用通过同一验收的 WebRTC 路线。[W3C 录制规范](https://www.w3.org/TR/mediastream-recording/#dom-mediarecorder-start) · [aiortc 服务端示例](https://github.com/aiortc/aiortc/tree/main/examples/server)

10 分钟先使用**一页** Moodle 测验，隔离翻页变量。建议 M2 用正常录制三次、每次约 600 秒作为起点。报告两轨可解码的实际覆盖，目标至少 99%，任一未解释缺口即记录缺陷，主动中断按真实缺口验收。每次在开头、中段、末尾做可见且可听的拍手动作，抽查回放定位误差目标 ≤1 秒。若分段方案靠大量重启间隙达不到目标，按上面的分块或 WebRTC 方案再测。后续用多页测验验证页面销毁、权限重新获取和队列恢复。所有门槛都报告实际测量值。

## 4. 从现有代码落地

### 第一步 · 本周做出可重演的小 Demo

1. 在现有实验机进入 `code/lab`，用 PowerShell 运行 `./start-demo.ps1`。脚本依赖已有的 WSL Ubuntu、Moodle 部署目录和两个容器，换机器按 README 先安装配置。打开 `http://localhost:8081/mod/quiz/view.php?id=6`。安排学生和教师使用两个独立的登录上下文。沿用本机已保存的演示配置。
2. 让另一位组员按说明从 Moodle 启动 SEB，点击录制，录 3–5 秒，等出新编号后交卷。教师按新作答编号找到对应素材，确认有画面和声音，点作答链接回到该答卷。留一份可分享的测试记录。
3. 试拒绝授权和学生直接打开回放。观察能否照常答题、提交。监控计数安排一次限时排查，在测试学生还在答题时，用老师查看对应 `Running Exams` 项目，记录页面变化和后台连接状态。
4. 11 月 19 日作为建议彩排日。按 11 月 13 日周会安排，**11 月 20 日前**向导师汇报已重现的考试、采集、回放结果，附当前监控计数问题和下一轮 10 分钟测试设计。近期演示依靠原型，后续开发另建测试测验和分支。[本机启动和现有演示步骤](code/lab/README.md)

**换一台电脑时的安装顺序**

1. 在 WSL Ubuntu 安装 Apache、PHP 及 Moodle 所需扩展和 MariaDB，导入已锁定的 Moodle 源码。Moodle 4.5 的 PHP 最低 8.1，使用 64 位版本，要求 `sodium` 和 `max_input_vars≥5000`，MariaDB 最低 10.6.7。配置 Moodle 数据目录和 cron，安装后先在普通浏览器用测试账号成功交卷。[Moodle 4.5 系统要求](https://moodledev.io/general/releases/4.5#server-requirements)
2. 按官方单机 Demo 指南准备 SEB Server Compose 和本地 `.env`，使用已验证的 2.2 镜像及独立数据库，再绑定 Moodle。仓库 SEB Server Demo 的 MariaDB 是给 SEB Server 容器用的。创建教师和学生，完成 E1 后安装自有插件，执行 `php admin/cli/upgrade.php --non-interactive`，按本机真实 `cmid` 配置自有插件并记录结果。记录 SEB Server 从容器访问 Moodle 和学生从 Windows 访问两个服务所需的各自地址。[SEB Server Demo 部署指南](https://seb-server-setup.readthedocs.io/en/latest/install-demo.html) · [自有插件安装说明](code/lab/README.md)
3. 在同一 WSL 环境创建 Python 虚拟环境，安装锁定的 Django 依赖、数据库驱动和 FFmpeg。配置数据库连接、媒体目录、Moodle 服务凭证和分析程序路径，执行 `python manage.py migrate`，开发阶段用 `python manage.py runserver`。联机时用 Gunicorn 启动 Django，Nginx 提供 HTTPS 及媒体转发。验证写入、授权回放和分析后再连接内网测试电脑。首次重装时整理版本表、配置示例和截图以供 M5 复现。[Django 与 Gunicorn 部署](https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/gunicorn/)

### 第二步 · 先做一条上传到回放的小链路

在 `code/evidence-server/` 创建 Python 虚拟环境，用 `django-admin startproject exam_guardian .` 建工程，用 `python manage.py startapp evidence` 建首个业务模块。添加考试、会话、片段和分配模型，执行 `python manage.py makemigrations`、`python manage.py migrate`。配置私有 `EG_MEDIA_ROOT`，用一个已获同意的测试 WebM，通过 Postman 或 `curl` 创建固定测试会话并上传。在 Django Admin 分配复核员，登录后在复核列表点开原片，回查表和文件，再接入 SEB。

上传视图从 `request.FILES` 读取 `UploadedFile`，用 `chunks()` 写临时文件并计算 SHA-256。检查大小、格式和双轨后存入按会话组织的最终路径。文件和数据都可用才确认保存。失败清理临时或未入库文件，定期对账。校验媒体格式和有效性使用 FFprobe。在播放接口检查会话分配，开发时用 `FileResponse` 播放短片。验收拖动时，由 Django 校验后通过 `X-Accel-Redirect` 交给 Nginx 的 `internal` 路径处理文件和 HTTP Range，实际检查拖动时的 `206` 响应与直接访问内部路径被拒绝。必要时重新封装并保留原件哈希。[Django 文件上传](https://docs.djangoproject.com/en/5.2/topics/http/file-uploads/) · [Nginx 内部路径](https://nginx.org/en/docs/http/ngx_http_core_module.html#internal)

### 第三步 · 让 Moodle 确认这是谁的第几次作答

1. 新增插件同源接口 `session.php`。学生阅读说明后提交同意或拒绝。PHP 校验当前登录、`sesskey`、活动范围、答题能力和作答属于当前用户。拒绝只登记状态并继续答题。同意后才发采集令牌并请求设备。仅对进行中的真实作答启用录制。教师预览依照现有做法可预览设备。
2. PHP 服务端用独立的服务凭证请求 Django 内部接口，发送 `sourceSite`、`cmid`、`quizId`、`attemptId` 和伪名化学生标识。`cmid` 是课程活动 ID，`quizId` 是测验实体 ID，`attemptId` 是某次作答 ID。用 `sourceSite + attemptId` 做会话唯一键，同一次刷新不新建，第二次作答另开。学生标识可由 PHP 按站点及 Moodle 用户 ID 生成稳定伪名。建议每个进行中的会话只允许一个活动录制页，重复打开显示状态并允许明确接手。
3. Django 返回 `sessionId`、会话相对时间基准和短期随机上传令牌。令牌只绑定当前会话和采集操作，哈希存储，可在 Moodle 重新核验后续期。客户端通过请求头携带令牌。教师浏览器使用独立 Django 账号和 Session Cookie。后端每次按令牌解析出来的会话写入，请求给别的会话 ID 时拒绝。学生只查询自己的会话状态。
4. 本机可用现有 Apache 将 `/eg-ingest/` 转发到 Django，使学生浏览器同源上传。联机时 Nginx 使用学生电脑可达的固定域名和可信 HTTPS，按路径把采集请求转发到 Gunicorn、考试请求转发到 Moodle Apache，教师复核用单独入口。内部注册接口仅供 Moodle 服务端调用。统一 Moodle 基础 URL、SEB Server 启动配置及相关回跳，重新生成 `.seb`。在 SEB 实机测试 `getUserMedia` 及同源上传。[浏览器设备权限说明](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)

### 第四步 · 把短片扩成长期会话

- `attempt-media.js` 增加采集状态，例如等待同意、正在录制、等待上传、已同步、设备失败。每段产生稳定 `segmentKey`，附带协商好的序号以及起止相对毫秒，先进入发送队列，后台顺序上传，服务确认后移除。当前 `upload.php` 有每次作答 10 段、每段 8 MB，以及时长 ≤12 秒的限制。10 分钟按 10 秒计约 60 段，新接口根据试验设置单段大小、会话配额和超时，保留旧入口作为原型演示即可。
- 重试用同一个 `segmentKey`。对 `sessionId + segmentKey` 建唯一约束，相同文件和元数据重复提交时返回原结果，冲突时单独记录。先用单上传者顺序发送，失败采用有上限的延迟重试。给断网积压设置总时长或体积上限，且在恢复后重传，不能恢复的部分显示为缺口。
- 一页录制通过后加入多页测试。在页面活跃时把完成的片段写入该站点的 IndexedDB，翻页后读取当前会话队列并继续发送。新页面按产品上真实可用的授权方式重新连接设备，期间产生的断点用时间轴标记。IndexedDB 的队列通过兼容验证后用于断网和翻页恢复；卸载或 SEB 退出时可能来不及落盘，最终缺口由服务端核对覆盖发现。文件发送和重试均在答题提交之外进行。[IndexedDB 使用说明](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API/Using_IndexedDB)
- Moodle 可在 `db/events.php` 监听 `mod_quiz\event\attempt_submitted`。让观察器写轻量本地记录，由 Moodle 计划任务重试通知 Django，避免证据服务故障拖住交卷。证据应用给在途片段一个短收尾窗口，核对会话截止时间内的片段、序号和覆盖，再标为完整或不完整。重复通知幂等。异常关闭或缺少通知的会话由服务端超时进入待核对状态，Moodle 作答状态与媒体状态分开显示。按钮手动停止和等待状态适合第一轮验证。[Moodle 4.5 事件观察器说明](https://moodledev.io/docs/4.5/apis/commonfiles)
- 记录 `serverStartAt`、`receivedAt`、设备时钟以及媒体 `startMs/endMs`。每次页面启动时从证据应用取得当前会话相对时间估计，用页面 `performance.now()` 计算随后经过的时间。解码时长和帧时间戳用于对齐与复核。设备时钟单独留作诊断，服务端时间用于收件和审计。页面切换时记录估计误差和空白区间。考场标签从配置快照写入会话，表示所用实验考场或工位。

## 5. 数据表、接口和页面

| 表 | 建议字段与约束 |
| --- | --- |
| `exam_config` | `id, source_site, cmid, quiz_id, location_label, capture_enabled, active_rule_profile_id, retention_days` |
| `evidence_session` | `id, exam_id, source_site, attempt_id, student_ref, consent_version, consent_at, started_at, ended_at, media_status, location_snapshot, expires_at`。唯一索引 `(source_site, attempt_id)` |
| `media_segment` | `id, session_id, segment_key, seq_no, start_ms, end_ms, received_at, path, size_bytes, sha256, media_status`。索引 `(session_id, start_ms)`。唯一键 `(session_id, segment_key)` |
| `capture_event` | `session_id, type, start_ms, end_ms, detail`，记录拒绝授权、断流、恢复、缺段 |
| `analysis_job`、`observation`、`flag`、`rule_profile` | 任务记录状态、异常及运行版本。观察存类型、时间、原片引用、工具版本。标记引用观察并存规则版本、原因、优先级。规则版本存阈值、权重与启用时间 |
| Django 用户和组、`review_assignment`、`review_entry`、`audit_log` | 复用 Django 内置用户和组。业务表记录会话分配、意见及修订引用、最小操作记录。意见保存作者、时间、处置类别和正文 |

数据库先用 Django 内置账号和组，增加 `exam_config`、`evidence_session`、`media_segment` 和 `review_assignment`。后续按功能增量迁移。以 `sessionId + startMs` 检索证据，用服务端路径生成规则存放文件。时间戳字段的单位写进接口契约。

| 接口或页面 | 用途 |
| --- | --- |
| `POST /internal/sessions/start`、`POST /internal/sessions/{id}/exam-ended` | Moodle 服务端登记可信的作答映射和结束信息 |
| `POST /eg-ingest/sessions/{id}/segments`、`GET /eg-ingest/sessions/{id}/status` | 学生持本会话令牌上传及查收，网络/设备状态事件可另加接收接口 |
| `/admin/exams`、`/admin/sessions` | 配置考试、位置、规则和保留期，查看采集状态及分配人选。管理员配置权限与查看媒体的权限可单独授予 |
| `/review/sessions`、`/review/sessions/{id}` | 复核员看已分配的会话，查看标记和媒体空白，写复核结论。评审成员看已分配的会话与已有结论，追加独立评论 |
| `GET /review/media/{segmentId}`、`POST /review/sessions/{id}/entries` | 每次校验会话分配，支持回放及保存意见。改判或改备注追加新版本，保留历史 |

复核页用一行时间轴显示录像可用区间、缺口、模型标记。点 `02:10–02:16 检出两张脸`，查找 `02:10` 所在片段，用 `video.currentTime = (flagStartMs - segmentStartMs) / 1000` 定位，提供前后片段及上下文增量。缺片时显示具体缺失范围。复核员可选「有合理解释」「需进一步复核」「证据不足」，填写说明后刷新验证意见持久化。评审评论带独立作者。模型重跑后保留旧标记引用，已有意见仍定位到原版本。

用同意参与的组员和测试账号产生素材。保留期按 v2 的拟议默认值设为最终评估后 30 天，允许管理员调整。到期进入删除流程，清除媒体、派生观察、标记与相关复核内容，清理未完成队列和相关测试副本，按约定留最小删除记录。删除失败标记待重试，并核验旧播放 URL 已不可访问。实验素材和令牌保存在指定环境。

## 6. 基础分析及论文实验

### 能直接实现的分析

1. **视觉**。用 FFmpeg、PyAV 或 OpenCV 读取视频，保留每帧实际相对时间。先抽样每秒 2 帧，在同一批帧上比较 MediaPipe Face Detector 和 OpenCV Haar。输出每帧检出数量，按连续观测合并成人脸缺失、单人脸或多人脸区间。按时间戳规则确定区间边界且记录最多半秒的抽样分辨率。两帧之间有媒体空洞时断开。拍摄光线不足或脸转开时如实记录误检。[MediaPipe Face Detector](https://developers.google.com/edge/mediapipe/solutions/vision/face_detector) · [OpenCV Haar 示例](https://docs.opencv.org/4.x/db/d28/tutorial_cascade_classifier.html)
2. **音频**。FFmpeg 提取 16 kHz 单声道的 16 位 PCM。用 `webrtcvad` 逐个 20 ms 音频帧处理，按连续活动合并成区间。用脚本输出 `VOICE_ACTIVITY`、起止毫秒和证据引用。背景人声也能触发，复核时播放原音。麦克风断开产生技术缺口，按片段状态标注。[WebRTC VAD 输入要求与示例](https://github.com/wiseman/py-webrtcvad)
3. **从观察生成标记**。Django 保存分析脚本返回的观察，例如 `faceCount=2, startMs=130000, endMs=136000`。一版试验规则可用「多人脸持续 ≥2 秒」「未检出人脸 ≥3 秒」「语音活动 ≥3 秒」，赋予管理员可配置的权重。会话排序取当前规则版本有效标记的权重累加，按研究需要在开发集冻结规则。把 `观察区间 + 持续时间 + 触发规则 + 证据链接` 显示给复核员，分值只用于排队。缺片按技术状态显示。
4. **对接分析任务**。先做命令 `python analyze.py --input <path> --output <json>`，定义 JSON 字段 `type, startMs, endMs, segmentId, toolVersion`。管理员按钮只建立待处理任务，由单独运行的 Django 管理命令领取已归档会话。命令用 `subprocess.run` 按参数列表调用分析脚本，记录超时和退出码，校验输出后入库。观察处理失败仍可人工回放。Django 根据当前规则生成标记，保存规则版本、触发原因和优先级。

### 怎么做实验和写结论

| 研究问题 | 操作 | 最终给导师看的数据 |
| --- | --- | --- |
| RQ1 采集与长时传输 | E1–E3、E6。Edge/SEB，稳定与受控断网，单页与翻页，记录每个配置。先一名考生，核心通过后测两名同时作答 | 总时长、双轨覆盖率、断流/恢复时长、回放定位误差、CPU/RAM、MB/分钟、事件归档延迟。区分上传耗时与分析耗时 |
| RQ2 集成与归属 | E4–E5。两名考生，各有独立作答，至少一人重复作答。用错会话令牌、同一分段重试、跨页继续，核对作答链接 | 每条路径的支持能力、安装维护成本、缺陷、最后选型。分别汇报 Moodle 真实作答和备用页测试会话 |
| RQ3 证据与人工复核 | 让没实现该页面的组员从标记打开正确片段，记录意见，再由评审追加评论。测试无分配的复核员、学生和删后的媒体 | 找到片段和提交意见耗时、授权与拒绝结果、修订历史、删除检查及反馈 |
| RQ4 检测及阈值 | 一张脸、无人脸、两张脸、语音、静音各至少 5 次；加入正常转头、逆光、背景声。两人校对人工区间，按完整录制会话划分开发集和留出集 | 两种视觉工具的结果、每类 TP/FP/FN、精准率和召回率、正常素材每分钟误报、处理耗时与典型漏报案例 |

阈值用 Excel 或 Python 就能比较。先在开发集对比两组持续时间，例如多人脸 1 秒与 2 秒。再固定一组跑留出集。每个预测只与一个同类标注配对，重叠时长除以合并时长至少 0.5 才计为命中，未匹配的预测是误报、未匹配的标注是漏报。举例，人工标记 20–25 秒，预测 21–26 秒，重叠 4 秒、合并 6 秒，匹配值约为 0.67。报告命中数、比例、样本总数以及环境条件。无可用素材的区间单独计入采集质量。

实验表至少记录 `run_id, source, versions, attempt_ref, setting, start/end, expected, actual, status, evidence_ref`。答辩时展示一个真实命中、一个误报或漏报，以及一个缺失段。展示技术路线选择、数据一致性和人工复核如何工作，团队试验数据用于说明这个环境下的效果和局限。

## 7. 里程碑和分工

| 日期或有效周 | A 采集与集成 | B 证据应用 | C 视觉 / D 音频与评价 | 过关产物 |
| --- | --- | --- | --- | --- |
| 11 月 16–20 日 | 复现 SEB、短片录制、交卷、监控实测 | 第二作答回查、拒权演练、汇总截图和说明 | 前期按可用性参加 | 可复演小 demo 与导师进度更新 |
| R1–R2 / M1 | 做不带自研脚本的 E1、记录版本 | 核对环境说明并复跑 | 备考 | 可复现基线及 E1 记录 |
| R3–R5 / M2 | 单页长录、WebRTC、嵌入与归属实验 | 验证证据应用选型，完成文件持久化、授权回放和最小会话映射 | 备考 | 一条双轨 10 分钟路线和选型报告 |
| R6–R9 | 断流、重连、多页、退出 | 队列去重、会话状态、用户分配及回放权限 | 备考 | E6 日志与权限走查 |
| R10–R13 / M3 | 接入可靠的归档通知与时间定位 | 四类角色、时间轴、意见、评审、审计 | 视觉与音频基线、样本标注 | 管理员、复核、评审能跑通，基础观察可点击追溯 |
| R14–R18 | 集成测试与联机复现 | 规则配置、删除、证据修订 | 阈值比较、复核练习 | 完整的一次考试到人工复核演练 |
| R19–R22 / M4 | 复跑异常和性能 | 验证验收清单 | 留出集、误报漏报与耗时 | 全流程 demo、评估结果和局限 |
| R23–R26 / M5 | 让另一人从说明部署 | 修核心问题和整理代码 | 完成实验、论文、图表 | 源码及版本、部署说明、允许交接的测试资料、最终报告和答辩材料 |

计划采用 v2 的 R1–R26 有效周，11 月 demo 是眼前的日历节点。A/B 前五个有效周各约 15 小时/周，备考期调整为各约 10 小时/周，C/D 考后按可用性进入项目安排。总计划工时 1080 小时，含 96 小时学习，另有 120 小时储备。组内每周核对任务证据，拟每两周和导师评审一次。学期停课、最终提交和角色实名由实际安排填入。[开题稿计划与验收](v2/Exam_Guardian_Project_Proposal_v2.md)

### 最终验收清单

- **FR01–04、FR12**：先同意再采集，状态可见，两个用户和重复作答关联正确，10 分钟双轨可播放，缺失标明，采集故障和标记场景下答题与交卷正常。
- **FR05–08、NF03–05**：停用或启用采集、配置分配及保留期、按时间回放、作者与修订可查、权限越界被拒、删除成功后回查无媒体。
- **FR09–11、NF01–02**：人脸和语音输出可复现，标记有理由和版本，规则可配置，模型观察、标记和意见可各自追溯。
- **FR15、NF06–08**：E1–E6 的测法、版本、判定、数据和限制齐全。另一队员能复现并报告实际资源开销。
- **FR13–14**：记录扩展的实际尝试、结果和交付状态。答辩以核心功能验收为主。

## 8. 只有 Java 和 Spring 基础，从哪里开始

你已有的 Web 后端思路可以迁移。Spring Controller 对应 Django View，实体和 Repository 的常见工作对应 Django Model 和 QuerySet。可以从 **B 的证据应用** 入手，先跑通一个小功能，再和 A 接 Moodle。下面按练习产物安排学习。

| 学什么 | 建议练习 | 起步投入 |
| --- | --- | --- |
| Python 基础和 Django 请求流程 | 学虚拟环境、字典、JSON 和异常。用 URL、View 和 `request.FILES` 上传一段 WebM，再用 `<video>` 回放 | 6–8 小时 |
| MariaDB、Django Model 和迁移 | 做会话和片段的一对多关系，建唯一约束，验证同一个请求两次只保存一条记录 | 3–5 小时 |
| Django 账号、组和管理后台 | 建两个测试账号，练习「具备复核角色」和「已被分配该作答」的两层校验，在回放接口也做检查 | 4–6 小时 |
| Django 模板和 JavaScript | 渲染会话列表和 `<video>`，练习 `fetch`、`FormData`、`currentTime`，在浏览器查看拖动时的 `206` | 4–6 小时 |
| Moodle 插件与身份 | 读 `attempt_panel.php` 和 `upload.php`，能讲清 `$USER`、`sesskey`、Quiz capability 与三个 ID，再让 `session.php` 请求证据应用 | 4–6 小时 |
| WebM、设备权限、网络基础 | 和 A 在 Edge、SEB 各采一段，学会复查同源、HTTPS、摄像头/麦克风权限，理解 `MediaStream`、`MediaRecorder` 与重试的关系 | 4–6 小时 |
| 分析脚本与证据应用对接 | 用 `ffprobe -show_streams -show_format -of json evidence.webm` 看轨道，再把一条带起止时间的 JSON 结果导入 Django | 3–4 小时 |

这些是上手练习估时。先复跑现有 Demo 并找到一段同意使用的 WebM。接着用 Django 保存短片，再做授权回放。第三步加作答映射、重复上传和越界访问测试，和 A 确认 Moodle 提供的字段。完成这个小实验再定框架，之后逐项接长录和复核。人脸与音频同学可用本地素材独立开发，按约定的 JSON 接入同一条时间轴。
