from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                            QFileDialog, QProgressBar)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.project_manager import project_manager
import os
import shutil

class UploadWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.selected_file = None
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("上传音频或文字稿")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 描述
        description = QLabel("支持的文件格式：\n音频文件：.wav, .mp3\n文字稿：.txt, .docx")
        description.setStyleSheet("color: #666666;")
        layout.addWidget(description)
        
        # 上传按钮
        self.upload_button = QPushButton("选择文件")
        self.upload_button.setStyleSheet("""
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
        """)
        self.upload_button.clicked.connect(self.select_file)
        layout.addWidget(self.upload_button)
        
        # 文件名标签
        self.file_label = QLabel()
        self.file_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.file_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # 处理按钮
        self.process_button = QPushButton("开始处理")
        self.process_button.setEnabled(False)
        self.process_button.setStyleSheet("""
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
        """)
        self.process_button.clicked.connect(self.process_file)
        layout.addWidget(self.process_button)
        
        # 添加底部空间
        layout.addStretch()
    
    def select_file(self):
        """选择要上传的文件"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("音频文件 (*.wav *.mp3);;文字稿 (*.txt *.docx)")
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.selected_file = selected_files[0]
                self.file_label.setText(f"已选择: {os.path.basename(self.selected_file)}")
                
                # 创建新项目目录
                project_manager.create_project()
                print(f"项目目录已创建: {project_manager.get_current_project()}")
                
                self.process_button.setEnabled(True)
    
    def process_file(self):
        """处理上传的文件"""
        try:
            if not self.selected_file:
                return
                
            # 根据文件类型处理
            file_ext = os.path.splitext(self.selected_file)[1].lower()
            
            if file_ext in ['.wav', '.mp3']:
                # 复制音频文件到项目目录
                audio_dir = project_manager.get_audio_dir()
                target_file = os.path.join(
                    audio_dir,
                    project_manager.get_audio_filename(
                        extension=file_ext
                    )
                )
                shutil.copy2(self.selected_file, target_file)
                
                # 切换到处理页面
                self.parent().parent().show_processing_page()
                
            elif file_ext in ['.txt', '.docx']:
                # 复制文字稿到项目目录
                transcript_dir = project_manager.get_transcript_dir()
                target_file = os.path.join(
                    transcript_dir,
                    os.path.basename(self.selected_file)
                )
                shutil.copy2(self.selected_file, target_file)
                
                # TODO: 直接处理文字稿生成总结
                pass
            
        except Exception as e:
            print(f"处理文件时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()