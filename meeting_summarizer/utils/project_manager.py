import os
import json
from datetime import datetime
from pathlib import Path

class ProjectManager:
    """项目目录管理类"""
    
    # 子目录名称常量
    AUDIO_DIR = "audio"
    TRANSCRIPT_DIR = "transcript"
    SUMMARY_DIR = "summary"
    CONFIG_FILE = "config.json"
    
    def __init__(self):
        # 获取用户主目录
        self.user_home = str(Path.home())
        # 默认项目根目录
        self.default_root = os.path.join(self.user_home, "meetingsummary")
        # 加载配置
        self.config = self._load_config()
        # 当前项目目录
        self.current_project = None
        
    def _load_config(self):
        """加载配置文件"""
        config_path = os.path.join(self.default_root, self.CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {str(e)}")
        
        # 默认配置
        default_config = {
            "root_dir": self.default_root,
            "last_project": None
        }
        
        # 确保目录存在
        os.makedirs(self.default_root, exist_ok=True)
        
        # 保存默认配置
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
            
        return default_config
    
    def _save_config(self):
        """保存配置到文件"""
        config_path = os.path.join(self.default_root, self.CONFIG_FILE)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")
    
    def set_root_dir(self, root_dir):
        """设置项目根目录"""
        if not os.path.exists(root_dir):
            os.makedirs(root_dir, exist_ok=True)
        self.config["root_dir"] = root_dir
        self._save_config()
    
    def get_root_dir(self):
        """获取项目根目录"""
        return self.config.get("root_dir", self.default_root)
    
    def create_project(self):
        """创建新项目目录"""
        # 生成项目目录名（年月日时分）
        project_name = datetime.now().strftime("%Y%m%d_%H%M")
        project_path = os.path.join(self.get_root_dir(), project_name)
        
        # 创建项目目录结构
        os.makedirs(project_path, exist_ok=True)
        os.makedirs(os.path.join(project_path, self.AUDIO_DIR), exist_ok=True)
        os.makedirs(os.path.join(project_path, self.TRANSCRIPT_DIR), exist_ok=True)
        os.makedirs(os.path.join(project_path, self.SUMMARY_DIR), exist_ok=True)
        
        # 更新当前项目
        self.current_project = project_path
        self.config["last_project"] = project_path
        self._save_config()
        
        return project_path
    
    def get_current_project(self):
        """获取当前项目目录"""
        if not self.current_project:
            return self.create_project()
        return self.current_project
    
    def get_audio_dir(self):
        """获取音频文件目录"""
        project_dir = self.get_current_project()
        return os.path.join(project_dir, self.AUDIO_DIR)
    
    def get_transcript_dir(self):
        """获取转写文件目录"""
        project_dir = self.get_current_project()
        return os.path.join(project_dir, self.TRANSCRIPT_DIR)
    
    def get_summary_dir(self):
        """获取总结文件目录"""
        project_dir = self.get_current_project()
        return os.path.join(project_dir, self.SUMMARY_DIR)
    
    def get_audio_filename(self, prefix="recording", extension=".wav"):
        """生成音频文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}{extension}"
    
    def get_transcript_filename(self, audio_filename, extension=".txt"):
        """根据音频文件名生成转写文件名"""
        base_name = os.path.splitext(audio_filename)[0]
        return f"{base_name}_transcript{extension}"
    
    def get_summary_filename(self, transcript_filename, extension=".txt"):
        """根据转写文件名生成总结文件名"""
        base_name = os.path.splitext(transcript_filename)[0]
        return f"{base_name}_summary{extension}"
    
    def list_projects(self):
        """列出所有项目目录"""
        root_dir = self.get_root_dir()
        if not os.path.exists(root_dir):
            return []
        
        projects = []
        for item in os.listdir(root_dir):
            project_path = os.path.join(root_dir, item)
            if os.path.isdir(project_path):
                # 检查是否包含必要的子目录
                if all(os.path.exists(os.path.join(project_path, d)) 
                      for d in [self.AUDIO_DIR, self.TRANSCRIPT_DIR, self.SUMMARY_DIR]):
                    projects.append(project_path)
        
        return sorted(projects, reverse=True)  # 最新的项目在前
    
    def switch_project(self, project_path):
        """切换到指定项目"""
        if not os.path.exists(project_path):
            raise ValueError(f"项目目录不存在: {project_path}")
        
        # 检查是否是有效的项目目录
        if not all(os.path.exists(os.path.join(project_path, d)) 
                  for d in [self.AUDIO_DIR, self.TRANSCRIPT_DIR, self.SUMMARY_DIR]):
            raise ValueError(f"无效的项目目录: {project_path}")
        
        self.current_project = project_path
        self.config["last_project"] = project_path
        self._save_config()
        
        return project_path
    
    def get_latest_transcript(self):
        """获取最新的转写文件路径"""
        try:
            transcript_dir = self.get_transcript_dir()
            if not os.path.exists(transcript_dir):
                return None
            
            # 查找最新的转写文件
            transcript_files = [f for f in os.listdir(transcript_dir) 
                              if f.endswith('_transcript.txt')]
            if not transcript_files:
                return None
            
            # 获取最新的文件
            latest_file = max(transcript_files, 
                            key=lambda x: os.path.getctime(os.path.join(transcript_dir, x)))
            return os.path.join(transcript_dir, latest_file)
            
        except Exception as e:
            print(f"获取最新转写文件时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

# 创建全局实例
project_manager = ProjectManager()
