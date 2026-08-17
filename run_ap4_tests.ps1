# AP4 Ask 范式（人机协同 / HITL）测试执行脚本
# date: 2026-08-17
# dev: 陈子毅
#
# 策略：
#   1) 优先：若已存在 venv 且装有 pytest，则用真实 pytest 运行
#      （JUnit XML 输出到 测试文档 目录 ap4_test_results.xml）
#   2) 回退：本机离线（无网络、无法 pip 安装 pytest / pydantic / openai-agents）时，
#      使用离线桩件运行器 C:\Users\15349\.workbuddy\ap4_offline_stubs\run_ap4_tests.py
#      （该运行器已硬编码将日志与 JUnit XML 写入 D:\桌面\agent大创\1\测试文档）

$ErrorActionPreference = "Continue"   # 不因回退而中断整个脚本
$RepoRoot = "D:\桌面\agent大创\1\AegisOS"
$VenvPy   = "C:\Users\15349\.workbuddy\binaries\python\envs\aegis\Scripts\python.exe"
$OfflinePy= "C:\Users\15349\.workbuddy\binaries\python\versions\3.13.12\python.exe"
$OfflineRunner = "C:\Users\15349\.workbuddy\ap4_offline_stubs\run_ap4_tests.py"
$OutDir   = "D:\桌面\agent大创\1\测试文档"
$LogFile  = Join-Path $OutDir "ap4_test_run.log"
$JunitXml = Join-Path $OutDir "ap4_test_results.xml"
$UsedOffline = $false

$env:PYTHONPATH = $RepoRoot

$TestFiles = @(
    "tests/aegisos_agents/perception/test_ask_mode.py",
    "tests/aegisos_agents/action/test_ir_planner_ask.py",
    "tests/aegisos_agents/action/test_critic_ask.py",
    "tests/aegisos_agents/action/test_threat_hunt_ask.py"
)

Write-Host "[AP4] 运行目录: $RepoRoot"

if (Test-Path $VenvPy) {
    Write-Host "[AP4] 检测到 venv：$VenvPy，尝试真实 pytest ..."
    & $VenvPy -m pytest @TestFiles -v --tb=short -p no:cacheprovider --junitxml=$JunitXml *> $LogFile
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -eq 0) {
        Write-Host "[AP4] pytest 成功（退出码 0）。日志: $LogFile | JUnit: $JunitXml"
        exit 0
    }
    Write-Host "[AP4] pytest 失败（退出码 $ExitCode），回退离线桩件运行器 ..."
} else {
    Write-Host "[AP4] 未检测到 venv，直接使用离线桩件运行器 ..."
}

# 离线回退：使用内置隔离 Python + 离线桩件运行器
$UsedOffline = $true
& $OfflinePy $OfflineRunner
$ExitCode = $LASTEXITCODE

Write-Host "[AP4] 离线运行器退出码: $ExitCode"
Write-Host "[AP4] 日志: $LogFile | JUnit: $JunitXml"
if ($UsedOffline) {
    Write-Host "[AP4] 注意：本次为离线桩件运行（非真实 pytest 运行时）。"
    Write-Host "[AP4]       权威回归请在可联网环境执行：pip install -e .[dev] && AEGIS_USE_MOCK=1 pytest tests/aegisos_agents -k ask"
}
exit $ExitCode
