from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                            QLabel, QPushButton, QSplitter, QTextEdit, QListWidgetItem,
                            QMessageBox, QWidget)
from PyQt6.QtCore import Qt
from utils.MeetingRecordProject import MeetingRecordProject
import os
from config.settings import Settings

class HistoryWindow(QDialog):
    # 定义操作类型常量
    ACTION_TRANSCRIBE = "transcribe"
    ACTION_EDIT_SUMMARY = "edit_summary"
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("历史会议记录")
        self.resize(1000, 600)
        
        # 设置为模态窗口
        self.setModal(True)
        
        self.selected_project = None  # 存储选中的项目对象
        self.selected_action = None   # 存储用户选择的操作
        self.settings = Settings()
        
        self.setup_ui()
        self.load_projects()

    def setup_ui(self):
        """设置界面"""
        main_layout = QVBoxLayout(self)  # 改用垂直布局作为主布局
        
        # 原有的水平分割布局
        content_layout = QHBoxLayout()
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧项目列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self.on_project_selected)
        
        left_layout.addWidget(QLabel("项目列表"))
        left_layout.addWidget(self.project_list)
        
        # 右侧内容显示
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 项目信息
        self.project_info = QLabel()
        right_layout.addWidget(self.project_info)
        
        # 文件内容显示
        self.content_display = QTextEdit()
        self.content_display.setReadOnly(True)
        right_layout.addWidget(self.content_display)
        
        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        content_layout.addWidget(splitter)
        main_layout.addLayout(content_layout)
        
        # 添加底部按钮区域
        button_layout = QHBoxLayout()
        
        self.transcribe_btn = QPushButton("音频转文字")
        self.edit_summary_btn = QPushButton("编辑会议总结")
        self.cancel_btn = QPushButton("取消")
        
        self.transcribe_btn.clicked.connect(self.on_transcribe)
        self.edit_summary_btn.clicked.connect(self.on_edit_summary)
        self.cancel_btn.clicked.connect(self.reject)  # 使用 QDialog 的 reject
        
        button_layout.addWidget(self.transcribe_btn)
        button_layout.addWidget(self.edit_summary_btn)
        button_layout.addStretch()  # 添加弹性空间
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        # 初始时禁用功能按钮
        self.transcribe_btn.setEnabled(False)
        self.edit_summary_btn.setEnabled(False)

    def load_projects(self):
        """加载所有项目"""
        try:
            project_root = self.settings.get("project", "project_root")
            if not os.path.exists(project_root):
                return
            
            # 获取所有项目目录
            project_dirs = []
            for item in os.listdir(project_root):
                project_path = os.path.join(project_root, item)
                if os.path.isdir(project_path):
                    project_dirs.append(project_path)
            
            # 按时间倒序排序
            project_dirs.sort(reverse=True)
            
            # 添加到列表
            for project_path in project_dirs:
                project_name = os.path.basename(project_path)
                item = QListWidgetItem(project_name)
                item.setData(Qt.ItemDataRole.UserRole, project_path)
                self.project_list.addItem(item)
                
        except Exception as e:
            print(f"加载项目列表时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_project_selected(self, current, previous):
        """当选择项目时"""
        if not current:
            return
            
        project_path = current.data(Qt.ItemDataRole.UserRole)
        project_name = os.path.basename(project_path)
        
        # 创建 MeetingRecordProject 对象
        self.selected_project = MeetingRecordProject(project_name)
        self.selected_project.project_dir = project_path
        self.selected_project.load_project_metadata()
        
        # 更新项目信息
        self.update_project_info(project_path)
        
        # 启用音频转文字按钮
        self.transcribe_btn.setEnabled(True)
        
        # 检查是否存在转写文件，决定是否启用编辑会议总结按钮
        transcript_file = self.selected_project.get_transcript_filename()
        self.edit_summary_btn.setEnabled(transcript_file and os.path.exists(transcript_file))

    def update_project_info(self, project_path):
        """更新项目信息显示"""
        try:
            # 获取项目名称
            project_name = os.path.basename(project_path)
            dt = datetime.strptime(project_name, "%Y%m%d_%H%M")
            date_str = dt.strftime("%Y年%m月%d日 %H:%M")
            
            # 获取音频文件信息
            audio_dir = os.path.join(project_path, "audio")
            audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.wav')]
            audio_count = len(audio_files)
            
            # 获取转写文件信息
            transcript_dir = os.path.join(project_path, "transcript")
            transcript_files = [f for f in os.listdir(transcript_dir) 
                              if f.endswith('_transcript.txt')]
            transcript_count = len(transcript_files)
            
            info_text = f"""
            会议时间：{date_str}
            录音文件：{audio_count} 个
            转写文件：{transcript_count} 个
            """
            self.project_info.setText(info_text)
            
        except Exception as e:
            self.project_info.setText(f"获取项目信息失败: {str(e)}") 

    def on_transcribe(self):
        """处理音频转文字请求"""
        if self.selected_project:
            self.selected_action = self.ACTION_TRANSCRIBE
            self.accept()

    def on_edit_summary(self):
        """处理编辑会议总结请求"""
        if self.selected_project:
            self.selected_action = self.ACTION_EDIT_SUMMARY
            self.accept()

    def accept(self):
        """当用户确认选择时"""
        if self.selected_project:
            super().accept()  # 关闭对话框并返回 accept
        else:
            QMessageBox.warning(self, "提示", "请先选择一个项目")

    def get_selected_project(self):
        """获取选中的项目对象"""
        return self.selected_project

    def get_selected_action(self):
        """获取用户选择的操作类型"""
        return self.selected_action