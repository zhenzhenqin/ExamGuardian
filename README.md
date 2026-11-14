# Exam Guardian · Moodle 与 SEB 小型演示

11 月 13 日周会安排在 11 月 20 日前更新进度。如果小 demo 就绪，就在 11 月 16–22 日这一周演示。

## 本机启动

本机已部署 Moodle 4.5.15+、SEB Server v2.2、官方 Moodle 插件 2.1 和 Windows SEB 3.10.2。以下入口基于已有 Ubuntu 和实验容器。首次部署另需配置 Moodle、API 账户和 SEB Server。

1. 在此目录用 PowerShell 执行 `./start-demo.ps1`，并让窗口保持打开。脚本在 Ubuntu 中复用原容器，并将 SEB Server 和它的 MariaDB 限制在 1.5 和 0.75 个逻辑 CPU 的配额。
2. 等 [Moodle 测验](http://localhost:8081/mod/quiz/view.php?id=6)和 [SEB Server](http://127.0.0.1:8080/gui)打开。测试账户信息在本机原有实验脚本中。
3. 如 Windows 浏览器刚启动时访问失败，稍等 Ubuntu 服务就绪。SEB Server 管理页可以用上面的 IPv4 入口。Moodle 站点地址使用配置中的 `localhost`。

## 约三分钟的展示流程

1. 用测试学生账号在普通 Edge 打开 **Exam Guardian Demo - Live**。展示 **Start Safe Exam Browser** 和 **Download SEB Server configuration file**。下载配置或点击启动，再用测试账号进入 SEB，完成两道判断题并提交。
2. 在 Moodle 教师端点击 **SEB Server monitoring**。浏览器会自动登录并打开这个测验的监控页。也可直接登录 SEB Server，在 **Running Exams** 选中测验。排练时确认正在作答的会话可见，提交后确认 Moodle 显示成绩。
3. 学生在 Windows SEB 中开始作答后，在试题上方点击「开始测试」。移动一下面前的物体并说话，确认预览和麦克风电平都响应。停止或离开页面后会释放设备。采集面板最多预览 10 秒。另有[独立录制测试页](http://localhost:8081/exam-guardian-media.html)可用于单独排查录制和回放。

## 作答页音视频

Moodle 加载 `local_examguardianmedia` 的 JavaScript，SEB 在打开作答页时执行。插件只在配置的测验作答页显示面板。本机已安装插件并配置为 Moodle 活动 6。SEB Server 的 **Exam Guardian Media** 考试配置已关联到该测验，其中 **Browser → Media Playback/Capture** 提供摄像头和麦克风选项。

在另一台实验环境部署时，将 `moodle-media` 的内容放入 Moodle 的 `local/examguardianmedia`，运行 `php admin/cli/upgrade.php --non-interactive`，用 `php admin/cli/cfg.php --component=local_examguardianmedia --name=cmid --set=6` 指定要测试的活动，按实际活动 ID 替换 6。

## 今晚复测

| 环节 | 结果 |
| --- | --- |
| Moodle 与 SEB Server | 两个入口均可访问 |
| 官方 Moodle 插件 | 课程 API 连接通过；启动配置重新生成成功 |
| Moodle 学生端 | 普通 Edge 只能看到 SEB 启动入口，实测下载到 473 字节的 `.seb` |
| 服务器监控页面 | 演示测验已出现在 Running Exams；Moodle 教师入口实测自动登录并进入该测验的监控页 |
| 音视频实验 | Edge 合成设备通过双轨采集、录制、回放、释放设备和 10 秒自动停止 |
| 作答页脚本 | Moodle 教师预览中，面板出现在题目上方，Edge 合成设备验证了双轨采集和释放设备 |
| Windows SEB 实机 | 客户端握手通过并取得演示测验配置。仅在本地演示配置中允许两块屏幕后，SEB 通过显示检查并启动考试客户端 |
| 当前阻塞 | 考试客户端检测到正在运行的 ToDesk，要求先结束该程序才能进入作答页。保留现有 ToDesk 进程，测试会话已经退出 |
| 排练待确认 | 在 ToDesk 已退出的本机上，用测试学生在 Windows SEB 中打开同一份测验，验证真实摄像头、麦克风、答题提交和教师端会话 |

Moodle 的内置 SEB 设置负责测验的客户端限制。SEB Server 官方插件通过 **Assessment Tool Setup**、**Assessment Tool Integration** 模板和 **Enable SEB Server** 串起自动导入、启动配置和教师监控。本次采用新的 **Exam Guardian Demo Connection**，解决旧配置解密失败后无法生成启动文件的问题。教师自动登录地址统一为 `http://localhost:8080`，与回跳地址使用同一个主机名。

AP Server、WebRTC 远端接收与持久化、Model Server 推理是后续实验。当前音视频页面在浏览器本地生成片段，供人工回放，也可按需保存。

11 月 19 日排练时，用 Windows SEB 完成学生作答、提交与教师监控，随后用真实摄像头和麦克风复测。11 月 20 日的进度更新可附上学生入口、成功下载配置和 Running Exams 的本机截图；实际完成的排练环节以当天记录为准。

## 版本管理

本仓库只跟踪演示源文件和说明。后续新增需要提交的源码时，先在 `.gitignore` 中加入该文件，再检查提交内容。每次功能调整验证后提交并推送 `main`。本地测试账号、媒体及生成的 `.seb` 留在实验环境中。

- [Moodle 官方 SEB 说明](https://docs.moodle.org/503/en/Safe_Exam_Browser)
- [SEB Server 官方 Moodle 集成步骤](https://seb-server.readthedocs.io/en/latest/lms_moodle.html)
