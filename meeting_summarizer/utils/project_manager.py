import os
from datetime import datetime
from pathlib import Path
from config.settings import Settings

class ProjectManager:
    """项目目录管理类"""
    
    # 子目录名称常量
    AUDIO_DIR = "audio"
    TRANSCRIPT_DIR = "transcript"
    SUMMARY_DIR = "summary"
    
    def __init__(self):
        """初始化项目管理器"""
        # 获取配置
        self.settings = Settings()
        # 默认项目根目录从settings获取
        self.default_root = self.settings.get("project", "project_root")
        print(f"默认项目根目录: {self.default_root}")
        
        # 确保根目录存在
        os.makedirs(self.default_root, exist_ok=True)
        
        # 当前项目目录
        self.current_project = None
        
        # 尝试加载上次的项目
        last_project = self.settings.get("project", "last_project")
        if last_project and os.path.exists(last_project):
            self.current_project = last_project
            print(f"加载上次项目: {self.current_project}")
        else:
            print("没有可用的上次项目")
    
    def set_root_dir(self, root_dir):
        """设置项目根目录"""
        if not os.path.exists(root_dir):
            os.makedirs(root_dir, exist_ok=True)
        self.settings.set("project", "project_root", root_dir)
        self.default_root = root_dir
    
    def get_root_dir(self):
        """获取项目根目录"""
        return self.default_root
    
    def create_project(self):
        """创建新项目目录"""
        # 生成项目目录名（年月日时分）
        project_name = datetime.now().strftime("%Y%m%d_%H%M")
        project_path = os.path.join(self.get_root_dir(), project_name)
        print(f"创建新项目目录: {project_path}")
        
        try:
            # 创建项目目录结构
            os.makedirs(project_path, exist_ok=True)
            os.makedirs(os.path.join(project_path, self.AUDIO_DIR), exist_ok=True)
            os.makedirs(os.path.join(project_path, self.TRANSCRIPT_DIR), exist_ok=True)
            os.makedirs(os.path.join(project_path, self.SUMMARY_DIR), exist_ok=True)
            
            # 更新当前项目
            self.current_project = project_path
            self.settings.set("project", "last_project", project_path)
            
            print(f"项目创建成功: {project_path}")
            return project_path
        except Exception as e:
            print(f"创建项目目录失败: {str(e)}")
            return None
    
    def get_current_project(self):
        """获取当前项目目录"""
        if not self.current_project:
            print("没有当前项目，创建新项目")
            return self.create_project()
        print(f"返回当前项目: {self.current_project}")
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
        self.settings.set("project", "last_project", project_path)
        
        return project_path
    
    def load_last_project(self):
        """加载上次的项目，仅在打开历史记录窗口时调用"""
        last_project = self.settings.get("project", "last_project")
        if last_project and os.path.exists(last_project):
            self.current_project = last_project
            print(f"加载上次项目: {self.current_project}")
            return True
        print("没有可用的上次项目")
        return False
    
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
