from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, 
                            QComboBox, QFrame, QHBoxLayout, QFileDialog, QApplication, 
                            QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.MeetingRecordProject import MeetingRecordProject
import os
from docx import Document
from utils.flexible_logger import Logger
import traceback

class SummaryWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.logger = Logger(
            name="summary_window",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self.project_manager = None
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
        
        main_layout.addWidget(summary_container)

    def set_summary(self, text):
        """Set summary text"""
        self.summary_text.setPlainText(text)
    
    def set_project_manager(self, project_manager):
        """Set project manager"""
        try:
            self.project_manager = project_manager
            self.logger.info(f"已设置项目管理器: {project_manager}")
        except Exception as e:
            self.logger.error(f"设置项目管理器失败: {str(e)}")
    
    def export_summary(self):
        """Export summary in selected format and language"""
        try:
            if not self.summary_text.toPlainText().strip():
                QMessageBox.warning(self, "错误", "没有可导出的内容")
                return
            
            # Get selected format and language
            export_format = self.format_combo.currentText()
            language = self.language_combo.currentText()
            
            # Get save file path
            file_filter = {
                "Markdown": "Markdown Files (*.md)",
                "Word": "Word Files (*.docx)"
            }
            
            file_extension = {
                "Markdown": ".md",
                "Word": ".docx"
            }
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存文件",
                "",
                file_filter[export_format]
            )
            
            if not file_path:
                return
                
            # Ensure correct file extension
            if not file_path.endswith(file_extension[export_format]):
                file_path += file_extension[export_format]
            
            content = self.summary_text.toPlainText()
            
            # Export based on selected format
            if export_format == "Markdown":
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
            elif export_format == "Word":
                doc = Document()
                doc.add_paragraph(content)
                doc.save(file_path)
            
            self.logger.info(f"已导出文件: {file_path}")
            QMessageBox.information(self, "成功", "导出成功！")
            
        except Exception as e:
            error_msg = f"导出失败: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"错误详情: {traceback.format_exc()}")
            QMessageBox.warning(self, "错误", error_msg)
    
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
            self.logger.error(f"加载总结文���时发生错误: {str(e)}")
            traceback.print_exc() 