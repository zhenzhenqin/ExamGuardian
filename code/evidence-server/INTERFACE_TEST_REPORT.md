# Exam Guardian 接口与功能验收

测试范围为 `exam_guardian/urls.py` 的 18 个应用入口、Moodle 自研插件的 4 个 PHP HTTP 入口，以及归档、分析、回放和到期清理。Django Admin 中检查项目使用的考试配置、分配、用户组和审计入口。Moodle 核心和官方 SEB Server 插件作为联调依赖。

## 本轮结果

| 测试层 | 实测结果 |
| --- | --- |
| Django 自动化测试 | 新增 14 项接口测试，连同原有 7 项用例，SQLite 与 MariaDB 10.11 各通过 21/21。Django 系统检查通过，无待生成迁移。 |
| Moodle 新版采集 | 两名测试学生各提交一次，分别确认 4 段和 3 段。交卷任务通知到 Django，宽限期后归档并标出实际缺段。同一学生重复作答时拒绝录制，仍正常交卷并保存零段。跨账号、缺少会话校验参数、交卷后重新登记被拒。Moodle 同源代理正确转发状态请求，并根据采集凭证允许或拒绝。 |
| Moodle 旧版接口 | 用两份合成文件验证上传、同内容重试、内容冲突、10 段上限、教师列表和文件校验值。教师拿到与原文件一致的字节，区间请求返回 206。学生访问和交卷后上传被拒。验证了已切换到新版采集的活动无法使用旧版上传接口。 |
| 合成设备浏览器回归 | 独立练习断网后恢复、翻页、交卷、Range 回放、复核修订和评审备注均通过。恢复后收到 3 段，期间缺段按预期标记为「部分素材缺失」。 |
| 后台任务 | 自动化测试覆盖归档宽限期、完整和缺段状态、分析排队与去重、分析产物、人工区间标签评价、过期文件和数据库记录清理。 |

修正了采集状态查询在数据库异常时未返回 503、事件编号冲突被当作成功、归档窗口结束仍接收事件、未开始作答可直接提交，以及无效修订编号的处理。Moodle 接入补齐缺失会话校验参数和无效同意值的处理。旧版教师页面明确限制读取方法，未知片段返回 404。

待做的软件环境验收为真实跨机 HTTPS 和可选 Nginx 媒体代发。Nginx 模式已验证 Django 生成的内部转发响应头。Windows SEB 真实摄像头和麦克风按约定稍后验收。此前 603 秒长录使用合成轨，详见[验收记录](ACCEPTANCE.md)。

## Django 入口

| 入口与方法 | 验收项目 |
| --- | --- |
| `GET /` | 调试模式进入练习，关闭练习时进入工作台，拒绝 POST |
| `GET/POST /admin/…` | 普通复核员被拒，管理员可调整考试配置、保留期和分配。拒绝给非复核角色分配，作答状态和审计记录保持只读 |
| `GET/POST /login/` | 登录表单、错误密码、有效密码、CSRF、登录态 |
| `POST /logout/` | CSRF、清除登录态、拒绝 GET |
| `GET /demo/` | 生成测试作答，翻页沿用作答，关闭练习模式后返回 404 |
| `GET /demo/capture.js` | 返回录制脚本和 JavaScript 类型，关闭练习模式后返回 404 |
| `POST /demo/session/` | 同意后签发凭证、拒绝时不签发、非法参数、禁用考试、无作答及 CSRF |
| `POST /demo/end/` | 完成后清除本次练习状态，再进入生成新作答，直接提交未开始的练习被拒 |
| `GET /health/` | 返回存活状态和禁止缓存，拒绝 POST |
| `POST /internal/moodle/start/` | 服务凭证、考试和学生映射、坏 JSON、非法字段、重复登记、禁用考试 |
| `POST /internal/moodle/end/` | 服务凭证、重复和未知作答通知、归档宽限期、完整和缺段状态 |
| `GET /eg-ingest/{id}/status/` | 准确返回状态和片段数。无凭证、过期凭证及删除中会话不可查询，数据库异常返回可重试的 503 |
| `POST /eg-ingest/{id}/segments/` | 双轨 WebM、格式和时间校验、文件及会话配额、同内容重试、内容冲突、跨作答凭证、关档后拒收 |
| `POST /eg-ingest/{id}/events/` | 状态词和时间范围、重复编号及内容冲突、关档期限、记录网络恢复 |
| `GET /review/` | 仅显示获分配记录、按作答筛选、按已完成分析的优先级排序，学生角色被拒 |
| `GET/POST /review/{id}/` | Moodle 答卷链接、复核和评审角色边界、备注保存和修订、空备注及异常修订编号 |
| `POST /review/{id}/analysis/` | 管理员可安排对已归档片段的分析，校验工具选项、拒绝重复排队和无权限调用 |
| `GET /review/media/{id}/` | 完整视频、区间和后缀读取、无效 Range、缺文件、未分配限制及 Nginx 内部转发响应头 |

## Moodle 自研接口

| 入口 | 验收项目 |
| --- | --- |
| `POST /local/examguardianmedia/session.php` | 本人作答登记、拒绝录制不影响交卷、Moodle 会话校验、他人作答被拒、无效同意值、交卷后重新登记被拒 |
| `POST /local/examguardianmedia/upload.php` | 旧版独立活动上传成功、校验格式和会话、同内容重试、冲突、每次作答的 10 段上限、交卷后拒绝新增 |
| `GET /local/examguardianmedia/index.php` | 教师查找作答、显示校验值、空结果、学生不可查询、非读取请求被拒 |
| `GET /local/examguardianmedia/clip.php` | 教师获得与原文件一致的字节、Range、学生不可读、未知片段返回 404、拒绝 POST |

## 复现

- 在 [部署说明](README.md) 的 Python 环境中先执行 `python manage.py fetch_face_model`，随后执行 `python manage.py test -v 2`。按说明分别使用 SQLite 和 MariaDB。只跑接口矩阵时使用 `python manage.py test evidence.test_interfaces -v 2`。
- 在独立的演示数据库中运行 `python tools/browser_acceptance.py --disrupt --seconds 21`。这条用例通过合成视频和音频验证断网、恢复、翻页、提交、回放及复核历史。
- 在回环 Moodle 上用 `tools/moodle_fixture.php` 创建测试活动和账号。对接 Django 后运行 `python tools/moodle_browser_acceptance.py --fixture var/moodle-fixture.json --output var/interfaces-moodle-results.json`。旧版测试需将 Moodle 插件的旧版 `cmid` 临时指向独立活动，并从 `evidencecmids` 排除此测试活动。对两份不同的合成 WebM 运行 `python tools/moodle_legacy_acceptance.py --fixture 本地配置.json --clip 合成片段A.webm --second-clip 合成片段B.webm`，测试完恢复原配置。
