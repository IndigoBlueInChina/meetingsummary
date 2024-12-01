# meetingsummary

## Project Overview:
The project aims to develop a Python-based AI script that generates summaries of meeting transcriptions from written text files. The script must utilize a locally installed Large Language Model (LLM), as we require an open-source solution that can be deployed on our Windows 11 PC with an Nvidia GPU and CUDA installed.

## Project Deliverables:

-    An AI script written in Python that can summarize meeting transcriptions.
-    Integration with an open-source LLM suitable for local deployment.
-    Documentation and support for the deployment and operation of the script.

```
会议记录总结系统 (Meeting Summary AI Assistant)
│
├── 前端模块 (Frontend)
│   ├── 文件上传界面
│   ├── 总结展示界面
│   └── 导出功能
│
├── 后端服务 (Backend)
│   ├── 文件处理服务
│   ├── AI推理服务
│   └── 总结生成服务
│
├── AI模型层 (AI Model Layer)
│   └── 本地开源大语言模型 (Local Open-Source LLM)
│
└── 存储模块 (Storage)
    ├── 会议记录文件存储
    └── 总结缓存
```
