# 编译桌面壳并复制到项目根目录：powershell -ExecutionPolicy Bypass -File webapp\build.ps1
# 需要 Rust（rustup 装的 stable 即可）；第一次编译要下载依赖，几分钟
$ErrorActionPreference = 'Stop'
$manifest = Join-Path $PSScriptRoot 'src-tauri\Cargo.toml'
cargo build --release --manifest-path $manifest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$exe = Join-Path $PSScriptRoot 'src-tauri\target\release\zjcs.exe'
$root = Split-Path $PSScriptRoot -Parent
Copy-Item $exe (Join-Path $root 'zjcs.exe') -Force
Write-Host "已生成 $(Join-Path $root 'zjcs.exe')"
