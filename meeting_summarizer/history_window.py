from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                            QLabel, QPushButton, QSplitter, QTextEdit, QListWidgetItem,
                            QMessageBox, QWidget, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.MeetingRecordProject import MeetingRecordProject
import os
from datetime import datetime
from config.settings import Settings

class HistoryWindow(QDialog):
    # 定义操作类型常量
    ACTION_TRANSCRIBE = "transcribe"
    ACTION_EDIT_SUMMARY = "edit_summary"
    ACTION_CLOSE = "close"
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("历史会议记录")
        self.resize(1000, 600)
        self.setModal(True)
        
        self.projects = []  # 存储 MeetingRecordProject 对象列表
        self.selected_project = None
        self.selected_action = None
        self.settings = Settings()
        
        self.setup_ui()
        self.load_projects()

    def setup_ui(self):
        """设置界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("历史记录")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        main_layout.addWidget(title)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧项目列表面板
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # 设置顶对齐
        left_layout.setContentsMargins(0, 0, 0, 0)  # 移除内边距
        
        # 项目列表标题
        list_title = QLabel("项目列表")
        list_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        left_layout.addWidget(list_title)
        
        # 项目列表
        self.project_list = QListWidget()
        self.project_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #EEEEEE;
            }
            QListWidget::item:selected {
                background-color: #33CCFF;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #F0F0F0;
            }
        """)
        self.project_list.currentItemChanged.connect(self.on_project_selected)
        left_layout.addWidget(self.project_list)
        
        # 右侧内容显示面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # 设置顶对齐
        right_layout.setContentsMargins(20, 0, 0, 0)
        
        # 内容显示区域
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # 设置顶对齐
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(0, 0, 0, 0)  # 移除内边距
        
        self.project_title = QLabel()
        self.project_title.setFont(QFont("Arial", 16))
        self.project_title.setStyleSheet("color: #333333;")
        
        self.summary_label = QLabel("会议总结")
        self.summary_label.setFont(QFont("Arial", 12))
        self.summary_label.setStyleSheet("color: #666666;")
        
        self.content_display = QTextEdit()
        self.content_display.setReadOnly(True)
        self.content_display.setStyleSheet("""
            QTextEdit {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
            }
        """)
        
        # 文件信息显示
        self.file_info = QLabel()
        self.file_info.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
                padding: 10px;
                background-color: #F5F5F5;
                border-radius: 5px;
            }
        """)
        
        content_layout.addWidget(self.project_title)
        content_layout.addWidget(self.summary_label)
        content_layout.addWidget(self.content_display)
        content_layout.addWidget(self.file_info)
        
        right_layout.addWidget(content_container)
        
        # 添加面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        main_layout.addWidget(splitter)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        # 主要按钮样式（蓝色）
        main_button_style = """
            QPushButton {
                background-color: #33CCFF;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 15px 30px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2CB5E8;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """
        
        # 次要按钮样式（灰色）
        secondary_button_style = """
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                border: none;
                border-radius: 5px;
                padding: 15px 30px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #CCCCCC;
            }
        """
        
        self.transcribe_btn = QPushButton("转写")
        self.transcribe_btn.setStyleSheet(main_button_style)
        
        self.edit_summary_btn = QPushButton("编辑总结")
        self.edit_summary_btn.setStyleSheet(main_button_style)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.setStyleSheet(secondary_button_style)  # 使用次要按钮样式
        
        self.transcribe_btn.clicked.connect(self.on_transcribe)
        self.edit_summary_btn.clicked.connect(self.on_edit_summary)
        self.close_btn.clicked.connect(self.on_close)
        
        button_layout.addWidget(self.transcribe_btn)
        button_layout.addWidget(self.edit_summary_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        
        # 初始时禁用功能按钮
        self.transcribe_btn.setEnabled(False)
        self.edit_summary_btn.setEnabled(False)

    def load_projects(self):
        """加载所有有效的项目"""
        try:
            project_root = self.settings.config_dir / "projects"
            if not os.path.exists(project_root):
                print(f"项目根目录不存在: {project_root}")
                return
            
            # 获取所有项目目录
            project_dirs = []
            for item in os.listdir(project_root):
                project_path = os.path.join(project_root, item)
                if os.path.isdir(project_path):
                    project_dirs.append(project_path)
        
            # 按时间倒序排序
            project_dirs.sort(reverse=True)
            
            # 创建并加载项目
            self.projects.clear()  # 清空现有项目列表
            self.project_list.clear()  # 清空列表控件
            
            print("\n=== 开始加载项目列表 ===")
            print(f"项目根目录: {project_root}")
            print(f"找到 {len(project_dirs)} 个项目目录")
            
            for project_path in project_dirs:
                project_name = os.path.basename(project_path)
                print(f"\n正在加载项目: {project_name}")
                print(f"项目路径: {project_path}")
                
                try:
                    
                    # 创建项目对象
                    project = MeetingRecordProject(project_name)

                    # 检查项目信息文件是否存在
                    if os.path.exists(project.project_info_path):
                        print(f"项目: {project.project_name} 路径: {project.project_dir}")

                        # 尝试加载项目元数据
                        project.load_project_metadata()
                        self.projects.append(project)
                        item = QListWidgetItem(project_name)
                        item.setData(Qt.ItemDataRole.UserRole, len(self.projects) - 1)
                        self.project_list.addItem(item)
                        print(f"成功加载项目: {project_name}")
                    else:
                        print(f"跳过无项目信息文件的项目: {project_name}")
                        
                except Exception as e:
                    print(f"加载项目 {project_name} 失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            print(f"\n=== 项目加载完成 ===")
            print(f"成功加载 {len(self.projects)} 个项目")
            print(f"跳过 {len(project_dirs) - len(self.projects)} 个无效项目")
                
        except Exception as e:
            print(f"加载项目列表时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_project_selected(self, current, previous):
        """当选择项目时"""
        if not current:
            return
            
        # 获取选中项目的索引
        project_index = current.data(Qt.ItemDataRole.UserRole)
        self.selected_project = self.projects[project_index]
        print(f"\n=== 已选择项目: {self.selected_project.project_name} ===")
        
        # 更新界面显示
        self.update_project_display()
        
        # 更新按钮状态
        self.update_button_states()

    def update_project_display(self):
        """更新项目信息显示"""
        try:
            # 显示项目标题
            dt = datetime.strptime(self.selected_project.project_name, "%Y%m%d_%H%M")
            title = dt.strftime("%Y年%m月%d日 %H:%M")
            self.project_title.setText(f"会议记录：{title}")
            
            # 获取项目内容
            metadata = self.selected_project.metadata
            if metadata.get('summary'):
                # 显示会议总结
                self.summary_label.setText("会议总结")
                print(f"会议总结: {metadata['summary']}")
                self.content_display.setText(metadata['summary'])
            elif metadata.get('transcript'):
                # 显示转写文本
                self.summary_label.setText("会议记录")
                print(f"会议记录: {metadata['transcript']}")
                self.content_display.setText(metadata['transcript'])
            else:
                # 清空内容显示
                self.summary_label.setText("项目信息")
                self.content_display.clear()
            
            # 显示文件信息
            self.file_info.setText(self._format_file_info())
            self.file_info.show()
            
        except Exception as e:
            print(f"更新项目显示时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def _format_file_info(self):
        """格式化文件信息显示"""
        info = []
        
        # 音频文件
        audio_files = self.selected_project.get_audio_filename()
        print(f"音频文件: {audio_files}")
        if os.path.exists(audio_files):
            info.append(f"音频文件 1 个):")
            info.append(f"  - {os.path.basename(audio_files)}")
            
        # 转写文件
        transcript_files = self.selected_project.get_transcript_filename()
        print(f"转写文件: {transcript_files}")
        if os.path.exists(transcript_files):
            info.append(f"\n转写文件 1 个):")
            info.append(f"  - {os.path.basename(transcript_files)}")
        
        # 总结文件
        if summary_files := self.selected_project.metadata.get('files', {}).get('summaries', []):
            info.append(f"\n总结文件 ({len(summary_files)} 个):")
            for f in summary_files:
                info.append(f"  - {os.path.basename(f)}")
        
        print(f"文件信息: {info}")

        return "\n".join(info) if info else "项目目录为空"

    def update_button_states(self):
        """更新按钮状态"""
        if not self.selected_project:
            self.transcribe_btn.setEnabled(False)
            self.edit_summary_btn.setEnabled(False)
            return
            
        metadata = self.selected_project.metadata
        has_audio = os.path.exists(self.selected_project.get_audio_filename())
        has_transcript = os.path.exists(self.selected_project.get_transcript_filename())
        
        self.transcribe_btn.setEnabled(has_audio and not has_transcript)
        self.edit_summary_btn.setEnabled(has_transcript)

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

    def on_close(self):
        """处理关闭请求"""
        # 直接关闭窗口，不做任何询问
        self.selected_action = self.ACTION_CLOSE
        self.reject()

    def get_selected_project(self):
        """获取选中的项目对象"""
        return self.selected_project

    def get_selected_action(self):
        """获取用户选择的操作类型"""
        return self.selected_action