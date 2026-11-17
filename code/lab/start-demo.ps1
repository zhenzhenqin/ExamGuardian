$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

wsl -d Ubuntu -u root -- install -m 0644 -- ./media-test.html /var/lib/seb-lab/moodle/exam-guardian-media.html
if ($LASTEXITCODE -ne 0) { throw '复制媒体测试页失败。请检查本机 Moodle 目录。' }

Write-Host '保持此窗口打开。另开窗口访问 http://localhost:8081/mod/quiz/view.php?id=6'
wsl -d Ubuntu -u root -- bash -lc 'set -e; systemctl start mariadb apache2 docker; docker update --cpus 0.75 seb-baseline-mariadb-1 >/dev/null; docker start seb-baseline-mariadb-1; docker update --cpus 1.5 seb-baseline-seb-server-1 >/dev/null; docker start seb-baseline-seb-server-1; exec docker wait seb-baseline-seb-server-1'
if ($LASTEXITCODE -ne 0) { throw '实验服务启动失败。请检查 Ubuntu 和原有实验容器。' }
