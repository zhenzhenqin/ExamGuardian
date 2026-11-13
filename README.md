# Exam Guardian · Moodle 与 SEB 小型演示

11 月 13 日周会安排在 11 月 20 日前更新进度。如果小 demo 就绪，就在 11 月 16–22 日这一周演示。

## 本机启动

本机已部署 Moodle 4.5.15+、SEB Server v2.2、官方 Moodle 插件 2.1 和 Windows SEB 3.10.2。以下入口基于已有 Ubuntu 和实验容器。首次部署另需配置 Moodle、API 账户和 SEB Server。

1. 在此目录用 PowerShell 执行 `./start-demo.ps1`，并让窗口保持打开。脚本在 Ubuntu 中复用原容器，并将 SEB Server 和它的 MariaDB 限制在 1.5 和 0.75 个逻辑 CPU 的配额。
2. 等 [Moodle 测验](http://localhost:8081/mod/quiz/view.php?id=6)和 [SEB Server](http://127.0.0.1:8080/gui)打开。测试账户信息在本机原有实验脚本中。
3. 如 Windows 浏览器刚启动时访问失败，稍等 Ubuntu 服务就绪。SEB Server 管理页可以用上面的 IPv4 入口。Moodle 站点地址使用配置中的 `localhost`。

## 约三分钟的展示流程

1. 用测试学生账号在普通 Edge 打开 **Exam Guardian Demo - Live**。展示 **Start Safe Exam Browser** 和 **Download SEB Server configuration file**。下载配置或点击启动，再用测试账号进入 SEB，完成两道判断题并提交。
2. 在教师端打开 Moodle 的 **SEB Server monitoring**，或在 SEB Server 的 **Running Exams** 选中这个测验。排练时确认正在作答的会话可见，提交后确认 Moodle 显示成绩。
3. 在[本地音视频页面](http://localhost:8081/exam-guardian-media.html)点击「录制音视频」，确认画面和麦克风电平。录 3–5 秒后点击停止并回放。最长录 10 秒，离开页面释放设备。先用普通浏览器排练。如需在 SEB 演示该页，以受支持的媒体配置打开此实验页面，核对摄像头与麦克风权限。使用团队测试设备和测试账号。

## 今晚复测

| 环节 | 结果 |
| --- | --- |
| Moodle 与 SEB Server | 两个入口均可访问 |
| 官方 Moodle 插件 | 课程 API 连接通过；启动配置重新生成成功 |
| Moodle 学生端 | 普通 Edge 只能看到 SEB 启动入口，实测下载到 473 字节的 `.seb` |
| 服务器监控页面 | 演示测验已出现在 Running Exams |
| 音视频实验 | Edge 合成设备通过双轨采集、录制、回放、释放设备和 10 秒自动停止 |
| 排练待确认 | Windows SEB 实测作答并提交、实时学生会话、真实摄像头和麦克风、同一场 Moodle 测验内的采集 |

Moodle 的内置 SEB 设置负责测验的客户端限制。SEB Server 官方插件通过 **Assessment Tool Setup**、**Assessment Tool Integration** 模板和 **Enable SEB Server** 串起自动导入、启动配置和教师监控。本次采用新的 **Exam Guardian Demo Connection**，解决旧配置解密失败后无法生成启动文件的问题。

AP Server、WebRTC 远端接收与持久化、Model Server 推理是后续实验。当前音视频页面在浏览器本地生成片段，供人工回放，也可按需保存。

- [Moodle 官方 SEB 说明](https://docs.moodle.org/503/en/Safe_Exam_Browser)
- [SEB Server 官方 Moodle 集成步骤](https://seb-server.readthedocs.io/en/latest/lms_moodle.html)
