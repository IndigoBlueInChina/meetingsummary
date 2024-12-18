from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, 
                            QComboBox, QFrame, QHBoxLayout, QFileDialog, QApplication, 
                            QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.MeetingRecordProject import MeetingRecordProject
import os
from docx import Document
from utils.flexible_logger import Logger
import traceback

class SummaryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger(
            name="summary_window",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self.project_manager = None
        
        # 设置窗口属性
        self.setWindowTitle("会议总结")
        self.setModal(True)  # 设置为模态对话框
        self.resize(800, 600)  # 设置合适的窗口大小
        
        self.init_ui()
        self.logger.info("SummaryWindow initialized")
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Top layout with title
        top_layout = QHBoxLayout()
        title = QLabel("会议总结")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        top_layout.addWidget(title)
        main_layout.addLayout(top_layout)
        
        # Summary content area
        summary_container = QWidget()
        summary_layout = QVBoxLayout(summary_container)
        
        # Summary text area
        summary_label = QLabel("总结内容")
        summary_label.setFont(QFont("Arial", 16))
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(summary_label)
        summary_layout.addWidget(self.summary_text)
        
        # Export options group
        export_group = QGroupBox("导出选项")
        export_layout = QHBoxLayout()
        
        # Language selection
        language_label = QLabel("输出语言:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["中文", "English"])
        export_layout.addWidget(language_label)
        export_layout.addWidget(self.language_combo)
        
        # Format selection
        format_label = QLabel("输出格式:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown", "Word"])
        export_layout.addWidget(format_label)
        export_layout.addWidget(self.format_combo)
        
        # Export button
        self.export_button = QPushButton("导出")
        self.export_button.clicked.connect(self.export_summary)
        export_layout.addWidget(self.export_button)
        
        export_group.setLayout(export_layout)
        summary_layout.addWidget(export_group)
        
        # 添加底部按钮布局
        button_layout = QHBoxLayout()
        
        # 添加关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)  # 使用 accept() 关闭对话框
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def set_project_manager(self, project_manager):
        """Set project manager"""
        try:
            self.project_manager = project_manager
            self.logger.info(f"已设置项目管理器: {project_manager}")
        except Exception as e:
            self.logger.error(f"设置项目管理器失败: {str(e)}")
    
    def load_summary(self):
        """Load summary content from project"""
        try:
            if not self.project_manager:
                raise ValueError("未设置项目管理器")
            
            summary_file = self.project_manager.get_summary_filename()
            if not summary_file or not os.path.exists(summary_file):
                self.summary_text.setText("未找到总结文件")
                return
            
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_text = f.read()
                self.summary_text.setPlainText(summary_text)
                
        except Exception as e:
            self.logger.error(f"加载总结文件时发生错误: {str(e)}")
            traceback.print_exc() 
    
    def show_summary(self):
        """显示总结对话框并加载内容"""
        self.load_summary()
        self.exec()  # 使用 exec() 显示模态对话框
    
    def export_summary(self):
        """Export the summary to a file or another destination."""
        # Implement the logic to export the summary here
        self.logger.info("Exporting summary...")
        # Example: Save to a file or display a dialog
        # ... your export logic ...