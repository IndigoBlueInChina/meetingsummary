from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, 
                            QComboBox, QFrame, QHBoxLayout, QFileDialog, QApplication, QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.MeetingRecordProject import MeetingRecordProject
import os
from docx import Document
from utils.llm_proofreader import TextProofreader
from utils.lecture_notes_generator import LectureNotesGenerator
from utils.meeting_notes_generator import MeetingNotesGenerator
from utils.flexible_logger import Logger
import traceback

class TranscriptWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.logger = Logger(
            name="transcript_window",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self.project_manager = None
        self.proofreader = TextProofreader()
        self.init_ui()
        self.logger.info("TranscriptWindow initialized")
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Top layout
        top_layout = QHBoxLayout()
        
        # Title
        title = QLabel("转写结果")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        top_layout.addWidget(title)
        
        # LLM status button
        self.llm_status_button = QPushButton()
        self.llm_status_button.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        self.llm_status_button.clicked.connect(self.open_llm_settings)
        top_layout.addWidget(self.llm_status_button)
        
        main_layout.addLayout(top_layout)
        
        # Transcript content area
        transcript_container = QWidget()
        transcript_layout = QVBoxLayout(transcript_container)
        transcript_label = QLabel("转写内容")
        transcript_label.setFont(QFont("Arial", 16))
        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        transcript_layout.addWidget(transcript_label)
        transcript_layout.addWidget(self.transcript_text)
        
        # Proofread button
        self.proofread_button = QPushButton("校对")
        self.proofread_button.clicked.connect(self.proofread_transcript)
        transcript_layout.addWidget(self.proofread_button)
        
        # Add status label (after proofread button)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                padding: 5px;
                font-style: italic;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        transcript_layout.addWidget(self.status_label)
        
        main_layout.addWidget(transcript_container)
        
        # Initial LLM status check
        self.check_llm_status()

    def load_content(self):
        """Load transcript content"""
        try:
            self.logger.info("开始加载转写内容")
            if not self.project_manager:
                raise ValueError("未设置项目管理器，无法加载内容")
            
            self.logger.info("开始加载转写文件...")
            self.load_transcriptfile()
            self.logger.info("内容加载完成")
            
        except Exception as e:
            self.logger.error(f"加载内容时发生错误: {str(e)}")
            traceback.print_exc()
    
    def load_transcriptfile(self):
        """Load transcript file"""
        try:
            if not self.project_manager:
                raise ValueError("未设置项目管理器")
            
            transcript_file = self.project_manager.get_transcript_filename()
            if not transcript_file or not os.path.exists(transcript_file):
                self.transcript_text.setText("未找到转写文件")
                return
            
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
                self.transcript_text.setPlainText(transcript_text)
            
        except Exception as e:
            self.logger.error(f"加载转写文件时发生错误: {str(e)}")
            traceback.print_exc()
    
    def proofread_transcript(self):
        """Handle proofreading request"""
        try:
            self.logger.info("开始校对文本...")
            self.proofread_button.setEnabled(False)
            self.proofread_button.setText("校对中...")
            
            current_text = self.transcript_text.toPlainText()
            if not current_text.strip():
                error_msg = "没有可用的文本内容"
                self.logger.warning(error_msg)
                QMessageBox.warning(self, "错误", error_msg)
                return
            
            try:
                self.logger.info("正在进行文本校对...")
                results = self.proofreader.proofread_text(current_text)
                
                if results and 'proofread_text' in results:
                    self.transcript_text.setPlainText(results['proofread_text'])
                    
                    if self.project_manager:
                        try:
                            new_transcript_file = self.project_manager.get_transcript_new_filename()
                            with open(new_transcript_file, 'w', encoding='utf-8') as f:
                                f.write(results['proofread_text'])
                            self.project_manager.add_proofread_transcript(new_transcript_file)
                            self.logger.info(f"校对文本已保存至: {new_transcript_file}")
                        except Exception as save_error:
                            error_msg = f"保存校对文本时发生错误: {str(save_error)}"
                            self.logger.error(error_msg)
                            QMessageBox.warning(self, "保存失败", error_msg)
                else:
                    error_msg = "校对结果格式错误"
                    self.logger.error(error_msg)
                    QMessageBox.warning(self, "校对失败", error_msg)
                    
            except Exception as e:
                error_msg = f"校对过程中发生错误：{str(e)}"
                self.logger.error(error_msg)
                self.logger.debug(f"错误详情: {traceback.format_exc()}")
                QMessageBox.warning(self, "校对失败", error_msg)
                
        except Exception as e:
            error_msg = f"校对功能发生错误: {str(e)}"
            self.logger.error(error_msg)
            self.logger.debug(f"错误详情: {traceback.format_exc()}")
            QMessageBox.warning(self, "错误", error_msg)
            
        finally:
            self.proofread_button.setEnabled(True)
            self.proofread_button.setText("校对")
            self.logger.info("校对操作结束")
    
    def set_transcript(self, text):
        """Set transcript text"""
        self.transcript_text.setPlainText(text)
    
    def set_project_manager(self, project_manager):
        """Set project manager"""
        try:
            self.project_manager = project_manager
            self.logger.info(f"已设置项目管理器: {project_manager}")
        except Exception as e:
            self.logger.error(f"设置项目管理器失败: {str(e)}")
    
    def check_llm_status(self):
        """Check LLM service status"""
        try:
            from utils.llm_statuscheck import LLMStatusChecker
            from config.settings import Settings
            
            settings = Settings()
            llm_config = settings._settings["llm"]
            checker = LLMStatusChecker(llm_config["api_url"])
            status = checker.check_status()
            
            if status == "ready":
                self.llm_status_button.setText("LLM服务正常")
                self.llm_status_button.setStyleSheet("""
                    QPushButton {
                        color: white;
                        background-color: #4CAF50;
                        border: none;
                        padding: 5px 10px;
                        border-radius: 3px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
            else:
                self.llm_status_button.setText("LLM服务离线")
                self.llm_status_button.setStyleSheet("""
                    QPushButton {
                        color: white;
                        background-color: #f44336;
                        border: none;
                        padding: 5px 10px;
                        border-radius: 3px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #da190b;
                    }
                """)
        except Exception as e:
            self.logger.error(f"检查LLM状态时发生错误: {str(e)}")
            self.llm_status_button.setText("LLM状态未知")
            self.llm_status_button.setStyleSheet("""
                QPushButton {
                    color: white;
                    background-color: #808080;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #666666;
                }
            """)

    def open_llm_settings(self):
        """Open LLM settings page"""
        # TODO: Implement settings page opening functionality
        print("TODO: 打开LLM设置页面")