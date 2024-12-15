from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, 
                            QComboBox, QFrame, QHBoxLayout, QFileDialog, QApplication, QMessageBox, QGroupBox, QSplitter, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from utils.MeetingRecordProject import MeetingRecordProject
import os
from docx import Document
from utils.llm_proofreader import TextProofreader
from utils.lecture_notes_generator import LectureNotesGenerator
from utils.meeting_notes_generator import MeetingNotesGenerator
from utils.flexible_logger import Logger
from utils.notes_processor_factory import NotesProcessorFactory
import traceback

class ProcessThread(QThread):
    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, processor_factory, processor_type, text):
        super().__init__()
        self.processor_factory = processor_factory
        self.processor_type = processor_type
        self.text = text
        self._stop_flag = False
        self.logger = Logger(
            name="process_thread",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )

    def run(self):
        try:
            self.logger.info(f"开始处理文本，处理器类型: {self.processor_type}")
            result = self.processor_factory.process_text(
                self.text,
                self.processor_type,
                self.progress_updated.emit
            )
            if not self._stop_flag:
                self.logger.info("文本处理完成，发送结果")
                self.finished.emit(result)
            else:
                self.logger.info("处理线程检测到停止信号，终止处理")
        except Exception as e:
            self.logger.error(f"处理文本时发生错误: {str(e)}")
            self.error.emit(str(e))

    def stop(self):
        """停止处理"""
        self.logger.info("接收到停止信号")
        self._stop_flag = True
        processor = self.processor_factory.get_processor(self.processor_type)
        if hasattr(processor, 'stop'):
            self.logger.info(f"正在停止 {self.processor_type} 处理器...")
            processor.stop()
            self.logger.info(f"{self.processor_type} 处理器已停止")
        self.logger.info("处理线程停止操作完成")

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
        self.processor_factory = NotesProcessorFactory()
        self.is_processing = False
        
        # 设置默认处理器类型
        self.current_processor_type = "basic"
        
        # 初始化UI
        self.init_ui()
        
        # 检查LLM状态
        self.check_llm_status()
        
        self.logger.info("TranscriptWindow initialized")
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Top layout with title, template selector and LLM status
        top_layout = QHBoxLayout()
        
        # Title and template selector group
        title_group = QHBoxLayout()
        
        # Title
        title = QLabel("转写内容")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_group.addWidget(title)
        
        # Add some spacing between title and template selector
        title_group.addSpacing(20)
        
        # Template selector
        template_label = QLabel("模板:")
        template_label.setFont(QFont("Arial", 12))
        self.template_combo = QComboBox()
        self.template_combo.addItems(["仅校对", "课堂笔记", "会议记录"])
        self.template_combo.setCurrentText("仅校对")
        self.template_combo.setFixedWidth(150)  # 设置固定宽度
        self.template_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #CCCCCC;
                border-radius: 5px;
                padding: 5px 10px;
                background: white;
                font-size: 12px;
                min-height: 25px;
            }
            QComboBox:hover {
                border: 2px solid #33CCFF;
            }
            QComboBox:focus {
                border: 2px solid #33CCFF;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                padding-right: 5px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(resources/icons/down-arrow.png);
            }
            QComboBox QAbstractItemView {
                border: 1px solid #CCCCCC;
                selection-background-color: #33CCFF;
                selection-color: white;
                background: white;
            }
        """)
        self.template_combo.currentIndexChanged.connect(self.on_template_changed)
        
        title_group.addWidget(template_label)
        title_group.addWidget(self.template_combo)
        title_group.addStretch()  # 添加弹性空间
        
        top_layout.addLayout(title_group)
        
        # LLM status button (靠右对齐)
        self.llm_status_button = QPushButton("检查LLM状态...")
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
        self.llm_status_button.clicked.connect(self.open_llm_settings)
        top_layout.addWidget(self.llm_status_button)
        
        main_layout.addLayout(top_layout)
        
        # 主要内容区域 - 使用 QSplitter 来管理垂直方向的布局
        content_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 转写内容区域 - 应该占据主要空间
        transcript_container = QWidget()
        transcript_layout = QVBoxLayout(transcript_container)
        transcript_layout.setContentsMargins(0, 0, 0, 0)
        
        transcript_label = QLabel("转写内容")
        transcript_label.setFont(QFont("Arial", 16))
        
        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        self.transcript_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
            }
        """)
        transcript_layout.addWidget(transcript_label)
        transcript_layout.addWidget(self.transcript_text)
        
        # 主题和关键字区域 - 固定高度
        info_container = QWidget()
        info_container.setFixedHeight(150)  # 设置固定高度
        info_layout = QHBoxLayout(info_container)
        info_layout.setSpacing(20)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Topic section
        topic_container = QWidget()
        topic_layout = QVBoxLayout(topic_container)
        topic_layout.setContentsMargins(0, 0, 0, 0)
        
        topic_label = QLabel("主题")
        topic_label.setFont(QFont("Arial", 12))
        
        self.topic_text = QTextEdit()
        self.topic_text.setMaximumHeight(100)
        self.topic_text.setPlaceholderText("会议主要讨论的内容...")
        self.topic_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
            }
            QTextEdit:focus {
                border: 1px solid #33CCFF;
            }
        """)
        
        topic_layout.addWidget(topic_label)
        topic_layout.addWidget(self.topic_text)
        info_layout.addWidget(topic_container)
        
        # Keywords section
        keywords_container = QWidget()
        keywords_layout = QVBoxLayout(keywords_container)
        keywords_layout.setContentsMargins(0, 0, 0, 0)
        
        keywords_label = QLabel("关键字")
        keywords_label.setFont(QFont("Arial", 12))
        
        self.keywords_text = QTextEdit()
        self.keywords_text.setMaximumHeight(100)
        self.keywords_text.setPlaceholderText("重要的关键词...")
        self.keywords_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                padding: 10px;
                background-color: white;
            }
            QTextEdit:focus {
                border: 1px solid #33CCFF;
            }
        """)
        
        keywords_layout.addWidget(keywords_label)
        keywords_layout.addWidget(self.keywords_text)
        info_layout.addWidget(keywords_container)
        
        # 添加到垂直分割器
        content_splitter.addWidget(transcript_container)
        content_splitter.addWidget(info_container)
        
        # 置分割器的初始大小比例
        content_splitter.setStretchFactor(0, 3)  # 转写内容区域占 3
        content_splitter.setStretchFactor(1, 1)  # 主题关键字区域占 1
        
        main_layout.addWidget(content_splitter)
        
        # 底部按钮和状态区域
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # 按钮和进度条布局
        button_progress_layout = QVBoxLayout()
        button_progress_layout.setSpacing(10)
        
        # 校对按钮
        self.proofread_button = QPushButton("校对")
        self.proofread_button.setStyleSheet("""
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
        self.proofread_button.clicked.connect(self.on_proofread_clicked)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #33CCFF;
                border-radius: 5px;
            }
        """)
        self.progress_bar.hide()  # 初始时隐藏进度条
        
        button_progress_layout.addWidget(self.proofread_button)
        button_progress_layout.addWidget(self.progress_bar)
        
        bottom_layout.addLayout(button_progress_layout)
        main_layout.addWidget(bottom_container)
        
        # 初始化校对状态
        self.is_processing = False

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
    
    def on_proofread_clicked(self):
        """处理校对按钮点击事件"""
        try:
            if not self.is_processing:
                self.start_proofreading()
            else:
                self.logger.info("用户点击停止按钮，准备停止处理...")
                if hasattr(self, 'process_thread'):
                    self.process_thread.stop()
                    self.logger.info("已发送停止信号到处理线程")
                self.reset_process_ui()
                self.logger.info("处理已停止，UI已重置")
                
        except Exception as e:
            self.logger.error(f"处理按钮点击事件失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"操作失败: {str(e)}")

    def start_proofreading(self):
        """开始文本处理"""
        try:
            current_text = self.transcript_text.toPlainText()
            if not current_text.strip():
                QMessageBox.warning(self, "错误", "没有可用的文本内容")
                return
            
            # 更新UI状态
            self.is_processing = True
            self.proofread_button.setText("停止")
            self.proofread_button.setStyleSheet("""
                QPushButton {
                    background-color: #FFB366;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 15px 30px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #FF9933;
                }
                QPushButton:disabled {
                    background-color: #CCCCCC;
                }
            """)
            
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            
            # 启动处理线程
            self.process_thread = ProcessThread(
                self.processor_factory,
                self.current_processor_type,
                current_text
            )
            self.process_thread.progress_updated.connect(self.update_progress)
            self.process_thread.finished.connect(self.on_process_finished)
            self.process_thread.error.connect(self.on_process_error)
            self.process_thread.start()
            
        except Exception as e:
            self.logger.error(f"启动处理失败: {str(e)}")
            self.reset_process_ui()
            QMessageBox.warning(self, "错误", f"启动处理失败: {str(e)}")

    def stop_proofreading(self):
        """停止文本处理"""
        if self.is_processing and hasattr(self, 'process_thread'):
            self.process_thread.stop()  # 设置线程的停止标志
            self.reset_process_ui()

    def update_progress(self, progress, status_text):
        """更新进度条"""
        self.progress_bar.setValue(progress)
        self.progress_bar.setFormat(f"{status_text} ({progress}%)")

    def on_process_finished(self, results):
        """文本处理完成处理"""
        try:
            if results and 'proofread_text' in results:
                self.transcript_text.setPlainText(results['proofread_text'])
                if self.project_manager:
                    new_transcript_file = self.project_manager.get_transcript_new_filename()
                    with open(new_transcript_file, 'w', encoding='utf-8') as f:
                        f.write(results['proofread_text'])
                    self.project_manager.add_proofread_transcript(new_transcript_file)
                    self.logger.info(f"文本处理已保存至: {new_transcript_file}")
        except Exception as e:
            self.logger.error(f"保存文本处理结果失败: {str(e)}")
            QMessageBox.warning(self, "保存失败", f"保存文本处理结果时发生错误: {str(e)}")
        finally:
            self.reset_process_ui()

    def on_process_error(self, error_msg):
        """文本处理错误处理"""
        self.logger.error(f"文本处理失败: {error_msg}")
        self.reset_process_ui()
        QMessageBox.warning(self, "文本处理失败", error_msg)

    def reset_process_ui(self):
        """重置文本处理相关的UI状态"""
        self.is_processing = False
        self.proofread_button.setText("校对")
        # 恢复按钮原来的蓝色样式
        self.proofread_button.setStyleSheet("""
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
        self.progress_bar.hide()
    
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

    def on_template_changed(self, index):
        """处理模板选择变化"""
        template = self.template_combo.currentText()
        self.logger.info(f"Template changed to: {template}")
        
        # 根据不同模板设置不同的提示文本
        if template == "仅校对":
            self.topic_text.setPlaceholderText("会议主要讨论的内容...")
            self.keywords_text.setPlaceholderText("重要的关键词...")
        elif template == "课堂笔记":
            self.topic_text.setPlaceholderText("课程主题和学习目标...")
            self.keywords_text.setPlaceholderText("课程重点和关键概念...")
        elif template == "会议记录":
            self.topic_text.setPlaceholderText("会议议题和目标...")
            self.keywords_text.setPlaceholderText("会议决议和关键行动项...")
        
        # 更新校对提示和处理逻辑
        self.update_proofread_template(template)

    def update_proofread_template(self, template):
        """更新处理模板"""
        if template == "仅校对":
            self.current_processor_type = "basic"
        elif template == "课堂笔记":
            self.current_processor_type = "lecture"
        elif template == "会议记录":
            self.current_processor_type = "meeting"
            
        self.logger.info(f"Processor type set to: {self.current_processor_type}")