# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_window.py'],  # 主程序入口
    pathex=[],
    binaries=[],
    datas=[
        ('assets\\*', 'assets'),  # 资源文件
        ('locales', 'locales'),   # 语言文件
        ('utils\\*', 'utils'),    # utils目录下的所有文件
        ('config\\*', 'config'),  # 配置文件
        ('audio_recorder\\*', 'audio_recorder'),  # 录音相关文件
        ('speech_to_text\\*', 'speech_to_text'),  # 语音转文字相关文件
        ('text_processor\\*', 'text_processor'),  # 文本处理相关文件
    ],
    hiddenimports=[
        # PyQt相关
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        
        # 系统模块
        'tkinter',
        'pathlib',
        'shutil',
        'datetime',
        'os',
        'sys',
        'json',
        'traceback',
        
        # 主要窗口模块
        'main_window',
        'recording_window',
        'processing_window',
        'transcript_window',
        'summary_window',
        'history_window',
        
        # utils模块
        'utils.MeetingRecordProject',
        'utils.flexible_logger',
        'utils.chunker',
        'utils.file_utils',
        'utils.language_detector',
        'utils.lecture_notes_generator',
        'utils.llm_factory',
        'utils.llm_proofreader',
        'utils.llm_statuscheck',
        'utils.meeting_notes_generator',
        'utils.notes_processor_factory',
        
        # audio_recorder模块
        'audio_recorder.recorder',
        
        # config模块
        'config.settings',
        
        # speech_to_text模块
        'speech_to_text.transcriber',
        
        # text_processor模块
        'text_processor.meeting_analyzer',
        'text_processor.summarizer',
        
        # 其他可能的依赖
        'numpy',
        'sounddevice',
        'soundfile',
        'wave',
        'scipy',
        'torch',
        'transformers',
        'jieba',
        'nltk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MeetingSummarizer',  # 生成的exe名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False表示不显示控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\app_icon.ico'  # 应用图标
)
