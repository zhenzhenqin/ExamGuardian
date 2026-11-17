# Exam Guardian 迭代记录

通过日期、功能范围、验证结果及未完成事项记录每次迭代。历史演示记录随 Git 原提交保留。

## 2026-11-14 演示原型

- 完成 Moodle、SEB Server、Windows SEB 的测验启动与提交验证。
- Moodle 插件支持学生明确启动后短时采集双轨 WebM，按真实作答保存和校验片段。
- 教师可按作答编号回放，学生回放访问被拒。监控入口成功跳转，学生计数仍待复测。

## 2026-11-16 至 17 实施方案

- 根据开题稿 v2、演示进度和 Moodle 4.5、SEB Server 官方文档制定分阶段交付计划。
- 比较 Django、FastAPI 和 Spring Boot。独立证据服务优先验证 Django，PHP、JavaScript 继续负责 Moodle 适配和浏览器采集。
