# Exam Guardian 本机验收与复现记录

2026 年 11 月 18 日（北京时间），仓库版本 2a54416。验收使用 Windows、WSL Ubuntu、Moodle 4.5.15+、SEB Server 2.2、Windows SEB 3.10.2.920、Django 5.2.19、MariaDB 10.11.14 和 Chromium 143.0.7499.4。电脑操作插件两次初始化均失败，页面操作与 PNG 取证改用项目的 Playwright 浏览器验收脚本。浏览器录制使用测试画布和 Web Audio 合成音轨。

## 验收结果

本机原型已跑通普通浏览器里的采集、上传、Moodle 作答关联、交卷归档、授权回放、人工复核和分析。完整的实机及论文验收仍有待补测项。

| 项目 | 本轮结果 | 证据 |
| --- | --- | --- |
| 启动与数据结构 | 新建 SQLite 库迁移成功，系统检查无异常，无待生成迁移。SQLite、MariaDB 分别通过 21/21 项测试。 | [系统和迁移检查](results/django-check.log) · [SQLite](results/django-tests.log) · [MariaDB](results/django-tests-mariadb.log) |
| 断网、翻页、复核 | 同一作答断网并恢复后翻页、提交。保存 4 段，整场覆盖 73.141%，最大缺口 4.489 秒，归档显示「部分素材缺失」。通过 Range 回放、意见修订、评审留言和未分配访问拒绝。 | [恢复后翻页](screenshots/standalone-03-reconnected-next-page.png) · [回放和缺口](screenshots/standalone-06-review-playback.png) · [实测数据](results/standalone.json) |
| 合成双轨长录 | 预热约 15 秒后，603 秒计时窗口覆盖 100%，窗口没有缺口。全程 619.122 秒、124 段、10,002,067 字节，覆盖 99.783%，最大缺口 0.650 秒，显示「已归档」。本轮是一场独立采集页测试。 | [长录归档和回放](screenshots/long-06-review-playback.png) · [实测数据](results/long.json) |
| Moodle 新版采集及关档 | 测试活动 8 的作答 15、16、17 全部为 Finished。作答 15 翻页沿用原作答，留存 4 段，双轨覆盖 77.179%，最大缺口 2.288 秒。作答 16 留存 3 段，覆盖 81.335%，最大缺口 2.377 秒。两次均因实际缺口标为「部分素材缺失」。作答 17 拒绝采集，留存 0 段并完成交卷。跨账号登记返回 403。 | [第二题继续录制](screenshots/moodle-03-recording-next-page.png) · [同意后交卷](screenshots/moodle-04-submitted-with-recording.png) · [拒绝后交卷](screenshots/moodle-06-submitted-after-decline.png) · [关档任务](results/moodle-close-tasks.log) |
| Moodle 授权回放与分析 | 分配复核员后可从证据页回跳 Moodle 答卷。源片段实际播放，32 字节 Range 请求返回 206，复核意见保存成功。MediaPipe 与 OpenCV Haar 均完成分析，各有 8 条观察、2 条标记，复核优先级均为 2。该合成场景的标记为「未检出人脸」。 | [授权回放](screenshots/moodle-08-authorized-playback.png) · [教师答卷](screenshots/moodle-11-teacher-answer-sheet.png) · [分析截图](screenshots/moodle-09-analysis-mediapipe.png) · [实测数据](results/moodle-evidence.json) |
| Moodle 旧版短录 | 在专用活动中复测两份合成 WebM，教师可查片段和 SHA-256，下载字节与原片一致，Range 返回 206。验证了上传重试、10 段上限、学生访问受限和交卷后拒绝新增。测试结束后恢复了原本的旧版活动配置。 | [教师片段清单](screenshots/legacy-01-teacher-media.png) · [测试结果](results/moodle-legacy.log) |
| SEB 入口 | 活动 6 从普通 Chromium 打开时显示 SEB 启动及配置下载，普通答题入口受限。SEB Server 登录页响应 200。 | [Moodle 启动入口](screenshots/seb-01-moodle-launch-gate.png) · [SEB Server 登录页](screenshots/seb-02-server-entry.png) |

## 验收材料

- [28 张测试截图](screenshots/)涵盖独立页断网和长录、Moodle 新旧采集、教师答卷、证据复核和 SEB 入口。
- [测试结果](results/)包含原始指标、Django 测试输出、模型校验值和关档记录。
- [复现脚本](scripts/)复用项目验收测试，并在关键页面保存截图。

## 在本机复现

### 1. 初始化隔离的证据服务

打开 PowerShell，进入 ExamGuardian 仓库根目录。已有 Python 环境无需重建。浏览器参数指定本机已有的 Chromium 143，因为当前 Playwright 默认对应的浏览器版本尚未安装。

~~~powershell
$qa = Join-Path $PWD 'docs\acceptance\2026-11-18'
Set-Location -LiteralPath '.\code\evidence-server'
$py = '.\.venv\Scripts\python.exe'
$run = Join-Path $PWD ('var\acceptance-repro-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $run | Out-Null
$env:EG_DEBUG = '1'
$env:EG_DB_NAME = ''
$env:EG_SQLITE = Join-Path $run 'standalone.sqlite3'
$env:EG_MEDIA_ROOT = Join-Path $run 'private'
$env:PYTHONIOENCODING = 'utf-8'
& $py manage.py migrate --noinput
& $py manage.py check
& $py manage.py makemigrations --check --dry-run
& $py manage.py fetch_face_model
& $py manage.py test -v 2
~~~

在当前窗口记录 $run 的完整路径，再启动服务并保持窗口打开。18591 用于隔离的独立练习。本机 Moodle 已使用 8091 访问联调证据服务。

~~~powershell
$run
& $py manage.py runserver 127.0.0.1:18591 --noreload
~~~

第二个 PowerShell 从仓库根目录开始，将 $run 设置成上面输出的路径，再执行以下命令。新截图和结果写入本地运行目录。

~~~powershell
$qa = Join-Path $PWD 'docs\acceptance\2026-11-18'
Set-Location -LiteralPath '.\code\evidence-server'
$py = '.\.venv\Scripts\python.exe'
$run = Read-Host '粘贴第一个窗口输出的完整运行目录'
$env:EG_DEBUG = '1'
$env:EG_DB_NAME = ''
$env:EG_SQLITE = Join-Path $run 'standalone.sqlite3'
$env:EG_MEDIA_ROOT = Join-Path $run 'private'
$env:PYTHONIOENCODING = 'utf-8'
$browser = Join-Path $env:LOCALAPPDATA 'ms-playwright\chromium_headless_shell-1200\chrome-headless-shell-win64\chrome-headless-shell.exe'
$env:EG_QA_DIR = $run
& $py "$qa\scripts\capture_acceptance.py" standalone --base http://127.0.0.1:18591 --chromium $browser --disrupt --seconds 21 --output "$run\standalone.json"
& $py "$qa\scripts\capture_acceptance.py" long --base http://127.0.0.1:18591 --chromium $browser --pre-roll 15 --seconds 603 --output "$run\long.json"
~~~

两轮脚本直接操作同意、录制、暂停、交卷和复核页面，并在关键步骤截图。长录判断通过的参考条件为计时窗口不少于 600 秒、双轨覆盖至少 99%、最大缺口不超过 1 秒。若另装匹配当前 Playwright 的 Chromium，可以省略 --chromium 参数。首次在另一台电脑搭建时，先看[证据服务部署说明](../../../code/evidence-server/README.md)和 [Moodle 与 SEB 实验环境说明](../../../code/lab/README.md)。

### 2. 复现普通浏览器 Moodle 集成

1. 在现有实验环境打开 Moodle 的测试活动 8。若 Moodle 或 SEB Server 未启动，按 [演示说明](../../../code/lab/README.md) 启动。确认已有联调证据服务 8091 可用。Windows 18591 是上一步独立练习的地址。
2. 在步骤 1 的第二个窗口执行以下命令。它使用现有本机测试账号，两个账号同意录制并提交，其中第一个翻页。第一个账号再考一次，点「拒绝采集」后交卷。

~~~powershell
& $py "$qa\scripts\capture_acceptance.py" moodle --base http://localhost:8081 --chromium $browser --fixture 'var\moodle-fixture.json' --output "$run\moodle.json"
~~~

3. 检查三条新作答编号。由 Moodle cron 运行新增的关档任务，或从测试队列查到对应任务 ID，逐条执行以下命令。本轮任务 ID 为 20、21、22，复现时以新任务 ID 为准。

~~~powershell
$taskId = Read-Host '输入当前作答对应的本地任务 ID'
wsl -d Ubuntu -u root -- sudo -u www-data php /var/lib/seb-lab/moodle/admin/cli/adhoc_task.php "--id=$taskId"
~~~

4. 等过录制会话的 120 秒上传宽限期。在同一终端复制并运行下列核对脚本。它使用本机 MariaDB 模式，逐条调用与 worker 相同的关档函数，仅处理这次的作答，并使用临时复核账号和分配验证播放及写入。分析调用后台使用的同一入口。

~~~powershell
. .\var\local-settings.ps1
& $egPython "$qa\scripts\verify_moodle.py" --chromium $browser
~~~

5. 手动核对时，以获分配的复核员身份打开工作台，搜索本轮作答编号。点片段播放，保存一条复核意见，再点「在 Moodle 查看答卷」，用实验教师账号查看相同作答编号。对拒绝录制的作答，确认 Moodle 显示 Finished，证据页没有可播放素材。截图可按 [Moodle 录制](screenshots/moodle-02-recording-confirmed.png)、[提交结果](screenshots/moodle-04-submitted-with-recording.png)、[复核](screenshots/moodle-08-authorized-playback.png)的顺序对照。

如需复跑 MariaDB 的 21 项自动化测试，在同一目录加载本机配置后执行 & $egPython manage.py test -v 2。该命令会创建并清理独立测试库。测试账号文件、媒体与配置凭证保存在本机实验目录。

### 3. 复现旧版短录接口

在本地测试站创建独立活动和测试账号，把插件的旧版 cmid 临时指向该活动，并确认该活动没有列进 evidencecmids。建议先用两份不同的合成 WebM 检查。运行后恢复旧版 cmid，当前本机原值为 6。不要对正式测验套用此步骤。详细配置见[旧版复现说明](../../../code/evidence-server/INTERFACE_TEST_REPORT.md#复现)。

~~~powershell
$fixture = Read-Host '输入新建的旧版 Moodle 测试账号文件路径'
$clip = Read-Host '输入第一份合成 WebM 路径'
$secondClip = Read-Host '输入第二份合成 WebM 路径'
& $py "$qa\scripts\capture_acceptance.py" legacy --chromium $browser --fixture $fixture --clip $clip --second-clip $secondClip
~~~

### 4. 下一阶段验收顺序

1. 用测试学生账号打开 Windows SEB 配置，进入活动 6。由本人同意摄像头和麦克风采集，至少确认两段，再翻页、交卷。两端核对同一作答编号、画面、可听音频、时间范围和缺口，再用复核员保存意见。当前活动 6 已启用新版采集面板，旧演示说明里的 10 秒自动停止和 EG 片段号对应旧版录制入口。
2. 另一台电脑或另一浏览器以教师身份打开 SEB Server 对应测验。在学生连接中和交卷后各记录一次监控名单及人数。仓库此前记录过连接存在而监控人数为 0，本轮只核对入口可用。
3. 在实际 Moodle + Windows SEB 环境先做三次单页长录，每次约 10 分钟。核对双轨覆盖至少 99% 和最大未解释缺口不超过 1 秒。单页稳定后再测多页，记录真实设备的翻页恢复、缺口和回放定位。
4. 使用学生机和教师机，通过可信 HTTPS 复跑提交、关档、授权回放、Range 和未分配访问。使用 Nginx 代发时核对媒体 Range 和内部路径权限，再实测并发容量。
5. 用经同意的标注素材做两轮人工标注，在团队留出集报告精确率、召回率和误报。

## 运行中遇到的问题

首次自动启动 Chromium 时，Playwright 默认浏览器文件缺失，改用本机已有的 Chromium 143 后完成测试。独立练习首次指向了已有的 8091，导致测试进程和页面连接到不同数据库，改用隔离的 18591 后重跑通过。旧版截图最初等待视频自动预加载超时，改在教师清单打开后直接取证，并用新测试活动完整重跑通过。复核截图最初使用的旧测试账号文件缺少教师账号，改用实验教师账号重新取证。浏览器测试与截图脚本保存在本目录。
