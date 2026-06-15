# 🚀 快速开始 - 使用 Opus 格式节省95%存储空间

## ⚡ 3步启用 Opus 格式

### 步骤 1：安装 FFmpeg

**Windows 用户（推荐）：**
```powershell
# 方法 1：使用我们的自动安装脚本（最简单）
.\install_ffmpeg.ps1

# 方法 2：使用 Chocolatey
choco install ffmpeg -y
```

验证安装：
```bash
ffmpeg -version
```

### 步骤 2：修改配置

编辑配置文件：`C:\Users\你的用户名\.meeting_summary\meeting_summary_config.json`

如果文件不存在，创建它：

```json
{
  "audio": {
    "format": "opus",
    "bitrate": "64k"
  }
}
```

### 步骤 3：重启应用

重新启动会议总结助手，新的录音将自动使用 Opus 格式！

## 📊 效果对比

**之前（WAV）：**
```
3小时会议 = 1.8 GB
10次会议 = 18 GB
```

**现在（Opus）：**
```
3小时会议 = 85 MB    ✅ 节省 95%
10次会议 = 850 MB    ✅ 节省 17 GB！
```

## 🎯 推荐配置

| 场景 | 格式 | 比特率 | 文件大小（1小时） |
|------|------|--------|------------------|
| **长时间会议（推荐）** | opus | 64k | 28 MB |
| 高质量录音 | opus | 96k | 42 MB |
| 兼容性最佳 | mp3 | 128k | 56 MB |
| 无损录音 | wav | - | 600 MB |

## 🔍 验证配置是否生效

启动录音后，查看控制台输出：

```
[record_audio] 音频格式: opus, 比特率: 64k
[save_segment] 开始保存片段 0 (格式: opus)...
[save_segment] 成功保存片段 0: recording_part000.opus (14.2 MB)
```

看到 `.opus` 文件就说明配置成功了！

## ❓ 常见问题

### Q: 我安装了 ffmpeg 但还是报错？
**A:** 重启命令行窗口或重启电脑，让 PATH 环境变量生效。

### Q: 转写功能还能正常工作吗？
**A:** 是的，FunASR 完全支持 Opus 格式，转写准确率不变。

### Q: 可以混合使用不同格式吗？
**A:** 可以，但建议统一使用一种格式以便管理。

### Q: 旧的 WAV 文件怎么办？
**A:** 保留或手动转换，不会影响新录音。

## 📚 更多信息

- 详细说明：`音频格式优化说明.md`
- 更新日志：`CHANGELOG.md`
- 问题反馈：提交 Issue

---

**祝您使用愉快！🎉**
