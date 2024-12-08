# meetingsummary

## 项目概述
本项目是一个基于 Python 的本地会议记录工具，能够录制会议音频并生成会议总结。项目使用本地部署的大语言模型，确保数据隐私安全。

## 主要功能

### 1. 音频录制
- ✅ 支持系统声音录制
- ✅ 支持麦克风输入（可选）
- ✅ 实时录音状态显示
- ✅ 暂停/继续功能
- ✅ 自动分段保存
- ✅ 录音时长显示

### 2. 音频转写
- ✅ 使用 FunASR 进行本地语音识别
- ✅ 支持中文语音识别
- ✅ 自动标点符号
- ✅ 支持长音频处理

### 3. 会议总结（开发中）
- 🚧 使用本地 LLM 生成会议摘要
- 🚧 提取关键决策点
- 🚧 识别行动项目

## 技术栈
- Python 3.11
- PyQt6 用于图形界面
- FunASR 用于语音识别
- soundcard 用于音频录制
- numpy 用于音频处理
- matplotlib 用于音频波形显示

## 安装说明

### 环境要求
- Python 3.11
- Ollama installed and running
- Qwen 2.5 model pulled in Ollama
- NLTK data

### 安装步骤

1. 克隆仓库
```bash
git clone [repository-url]
cd meetingsummary
```

2. 安装依赖
```bash
pip install poetry
poetry install
```

3. 运行程序
```bash
poetry run python meeting_summarizer/main_window.py
```

## 使用说明

### 录音功能
1. 点击"开始录音"按钮开始录制
2. 可选择是否启用麦克风输入
3. 录音过程中可以暂停/继续
4. 点击"结束"按钮停止录音
5. 录音文件会自动保存在项目目录下的 audio 文件夹中

### 音频转写
1. 录音结束后自动进入转写页面
2. 使用 FunASR 进行本地语音识别
3. 转写结果保存在 transcript 文件夹中

## 项目结构
```
meetingsummary/
├── meeting_summarizer/
│   ├── audio_recorder/
│   │   ├── recorder.py        # 音频录制核心功能
│   │   └── status.py         # 录音状态管理
│   ├── speech_to_text/
│   │   └── transcriber.py    # 语音识别模块
│   ├── text_processor/
│   │   └── summarizer.py     # 文本处理模块（开发中）
│   ├── utils/
│   │   └── project_manager.py # 项目管理工具
│   ├── main_window.py        # 主窗口和程序入口
│   ├── recording_window.py   # 录音界面
│   └── processing_window.py  # 处理界面
├── projects/                 # 项目文件存储
│   └── [项目名称]/
│       ├── audio/           # 录音文件
│       ├── transcript/      # 转写文本
│       └── summary/        # 会议总结
└── poetry.lock              # 依赖版本锁定文件
```

## 开发计划

- [ ] 优化会议总结功能，提取关键决策点，识别行动项目
- [ ] 增加会议总结模版功能，用户可选择模版生成会议总结，或者自定义模版
- [ ] 增加会议总结导出功能，支持导出为 PDF 格式，Word 格式，Markdown 格式
- [ ] 增加历史会议记录功能，用户可查看历史会议记录，并进行编辑，删除，导出等操作
- [ ] 改进用户界面，优化图标，优化布局
- [ ] 修复波形图显示问题
- [ ] 添加配置选项，Ollama 模型地址配置，OpenAI API Key 配置
- [ ] 添加配置选项，录音文件保存路径配置
- [ ] 增加各平台打包功能，Windows，Mac，Linux 
- [ ] 增加录音文件导入功能，支持导入已有的录音文件
  
  


## 贡献指南
欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证
MIT License