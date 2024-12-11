from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                            QLabel, QPushButton, QSplitter, QTextEdit, QListWidgetItem,
                            QMessageBox, QWidget)
from PyQt6.QtCore import Qt
from utils.project_manager import project_manager
from utils.file_utils import read_file_content
import os
from datetime import datetime

class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("历史会议记录")
        self.resize(1000, 600)
        
        # 设置为模态窗口
        self.setModal(True)
        
        self.setup_ui()
        
        # 加载上次的项目
        project_manager.load_last_project()
        
        # 加载历史记录
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
        self.project_list.clear()
        projects = project_manager.list_projects()
        
        for project_path in projects:
            # 获取项目名称（文件夹名）
            project_name = os.path.basename(project_path)
            try:
                # 尝试将项目名称转换为日期时间
                dt = datetime.strptime(project_name, "%Y%m%d_%H%M")
                display_name = dt.strftime("%Y年%m月%d日 %H:%M")
            except:
                display_name = project_name
                
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, project_path)  # 存储完整路径
            self.project_list.addItem(item)

    def on_project_selected(self, current, previous):
        """当选择项目时"""
        if not current:
            return
            
        project_path = current.data(Qt.ItemDataRole.UserRole)
        
        # 更新项目信息
        self.update_project_info(project_path)
        
        # 启用功能按钮
        self.transcribe_btn.setEnabled(True)
        self.edit_summary_btn.setEnabled(True)
        
        # 加载最新的转写文件
        transcript_dir = os.path.join(project_path, "transcript")
        if os.path.exists(transcript_dir):
            transcript_files = [f for f in os.listdir(transcript_dir) 
                              if f.endswith('_transcript.txt')]
            if transcript_files:
                latest_file = max(transcript_files, 
                                key=lambda x: os.path.getctime(os.path.join(transcript_dir, x)))
                file_path = os.path.join(transcript_dir, latest_file)
                try:
                    content = read_file_content(file_path)
                    self.content_display.setText(content)
                except Exception as e:
                    self.content_display.setText(f"读取文件失败: {str(e)}")
            else:
                self.content_display.setText("未找到转写文件")
        else:
            self.content_display.setText("未找到转写目录")

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
        current_item = self.project_list.currentItem()
        if not current_item:
            return
            
        project_path = current_item.data(Qt.ItemDataRole.UserRole)
        # TODO: 实现音频转文字功能
        QMessageBox.information(self, "提示", "音频转文字功能待实现")

    def on_edit_summary(self):
        """处理编辑会议总结请求"""
        current_item = self.project_list.currentItem()
        if not current_item:
            return
            
        project_path = current_item.data(Qt.ItemDataRole.UserRole)
        # TODO: 实现编辑会议总结功能
        QMessageBox.information(self, "提示", "编辑会议总结功能待实现")