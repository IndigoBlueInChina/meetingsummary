# This file will save all the default settings

import os
import json
from pathlib import Path

class Settings:
    def __init__(self):
        # 默认设置值
        self._defaults = {
            "audio": {
                "input_device": 0,  # 默认音频输入设备
                "sample_rate": 16000,  # 采样率
                "channels": 1,  # 单声道
                "chunk_size": 1024,  # 音频块大小
                "format": "opus",  # 音频格式: wav, mp3, opus
                "bitrate": "64k",  # 音频比特率（用于压缩格式）
            },
            "transcription": {
                "language": "zh",  # 默认语言
                "model": "base",  # 模型大小
                "device": "cpu",  # 运行设备
            },
            "summary": {
                "max_length": 500,  # 摘要最大长度
                "min_length": 100,  # 摘要最小长度
            },
            "output": {
                "save_audio": True,  # 是否保存录音文件
                "save_transcript": True,  # 是否保存转录文本
                "output_dir": str(Path.home() / "MeetingSummary"),  # 默认输出目录
            },
            "project": {
                "project_root": str(Path.home() / "MeetingSummary/Projects"),  # 项目根目录
                "last_project": None,  # 上次打开的项目路径
            },
            "llm": {
                "provider": "ollama",  # 默认提供者
                "model_name": "qwen2.5",
                "api_url": "http://localhost:11434",
                "api_key": "",  # OpenAI API密钥
            },
        }
        
        # 用户配置文件路径
        self.config_dir = Path.home() / ".meeting_summary"
        self.config_file = self.config_dir / "meeting_summary_config.json"
        
        # 初始化设置
        self._settings = self._defaults.copy()
        self._load_settings()

    def _load_settings(self):
        """从配置文件加载设置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                # 更新默认设置
                self._update_nested_dict(self._settings, user_settings)
            except Exception as e:
                print(f"加载配置文件时出错: {e}")

    def _save_settings(self):
        """保存设置到配置文件"""
        try:
            # 确保配置目录存在
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件时出错: {e}")

    def _update_nested_dict(self, d1, d2):
        """递归更新嵌套字典"""
        for k, v in d2.items():
            if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                self._update_nested_dict(d1[k], v)
            else:
                d1[k] = v

    def get(self, section, key):
        """获取设置值"""
        return self._settings.get(section, {}).get(key)

    def set(self, section, key, value):
        """更新设置值"""
        if section in self._settings and key in self._settings[section]:
            self._settings[section][key] = value
            self._save_settings()
        else:
            raise KeyError(f"Invalid setting: {section}.{key}")

    def get_all(self):
        """获取所有设置"""
        return self._settings.copy()

    def reset_to_defaults(self):
        """重置为默认设置"""
        self._settings = self._defaults.copy()
        self._save_settings()
