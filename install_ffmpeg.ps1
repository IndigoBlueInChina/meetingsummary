# FFmpeg 快速安装脚本（Windows）
# 用法：以管理员身份运行 PowerShell，然后执行：
# .\install_ffmpeg.ps1

Write-Host "================================" -ForegroundColor Cyan
Write-Host " FFmpeg 自动安装脚本" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# 检查是否已安装
try {
    $ffmpegVersion = ffmpeg -version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ FFmpeg 已经安装！" -ForegroundColor Green
        ffmpeg -version | Select-Object -First 1
        Write-Host "`n无需重复安装。" -ForegroundColor Yellow
        exit 0
    }
} catch {}

Write-Host "FFmpeg 未安装，开始安装过程...`n" -ForegroundColor Yellow

# 检查是否安装了 Chocolatey
try {
    $chocoVersion = choco --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 检测到 Chocolatey" -ForegroundColor Green
        $useChoco = $true
    } else {
        $useChoco = $false
    }
} catch {
    $useChoco = $false
}

if ($useChoco) {
    # 使用 Chocolatey 安装
    Write-Host "`n正在使用 Chocolatey 安装 FFmpeg..." -ForegroundColor Cyan
    Write-Host "这可能需要几分钟，请耐心等待...`n" -ForegroundColor Yellow
    
    choco install ffmpeg -y
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✓ FFmpeg 安装成功！" -ForegroundColor Green
        
        # 刷新环境变量
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        # 验证安装
        Write-Host "`n验证安装..." -ForegroundColor Cyan
        ffmpeg -version | Select-Object -First 1
    } else {
        Write-Host "`n✗ FFmpeg 安装失败" -ForegroundColor Red
        Write-Host "请手动安装或联系管理员。" -ForegroundColor Yellow
        exit 1
    }
} else {
    # 提供手动安装指南
    Write-Host "Chocolatey 未安装，提供两种安装方案：`n" -ForegroundColor Yellow
    
    Write-Host "方案 1：安装 Chocolatey 并使用它安装 FFmpeg（推荐）" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Gray
    Write-Host "1. 以管理员身份运行 PowerShell" -ForegroundColor White
    Write-Host "2. 执行以下命令：" -ForegroundColor White
    Write-Host ""
    Write-Host "Set-ExecutionPolicy Bypass -Scope Process -Force" -ForegroundColor Green
    Write-Host "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072" -ForegroundColor Green
    Write-Host "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" -ForegroundColor Green
    Write-Host ""
    Write-Host "3. 安装完成后执行：" -ForegroundColor White
    Write-Host "choco install ffmpeg -y" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "`n方案 2：手动下载并配置 FFmpeg" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Gray
    Write-Host "1. 下载 FFmpeg：" -ForegroundColor White
    Write-Host "   https://github.com/BtbN/FFmpeg-Builds/releases" -ForegroundColor Blue
    Write-Host "   选择：ffmpeg-master-latest-win64-gpl.zip" -ForegroundColor White
    Write-Host ""
    Write-Host "2. 解压到：C:\ffmpeg" -ForegroundColor White
    Write-Host ""
    Write-Host "3. 添加环境变量：" -ForegroundColor White
    Write-Host "   - 打开'系统属性' -> '环境变量'" -ForegroundColor White
    Write-Host "   - 编辑'Path'变量" -ForegroundColor White
    Write-Host "   - 添加：C:\ffmpeg\bin" -ForegroundColor Green
    Write-Host ""
    Write-Host "4. 重启命令行窗口并验证：" -ForegroundColor White
    Write-Host "   ffmpeg -version" -ForegroundColor Green
    Write-Host ""
    
    # 询问用户是否现在安装 Chocolatey
    $response = Read-Host "`n是否现在安装 Chocolatey？(Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        Write-Host "`n正在安装 Chocolatey..." -ForegroundColor Cyan
        
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✓ Chocolatey 安装成功！" -ForegroundColor Green
            Write-Host "正在安装 FFmpeg..." -ForegroundColor Cyan
            
            # 刷新环境变量以识别 choco 命令
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            
            choco install ffmpeg -y
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "`n✓ FFmpeg 安装成功！" -ForegroundColor Green
                ffmpeg -version | Select-Object -First 1
            }
        } else {
            Write-Host "`n✗ Chocolatey 安装失败" -ForegroundColor Red
            Write-Host "请参考上面的手动安装指南。" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "安装完成后，请重启应用程序" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# 等待用户按键
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
