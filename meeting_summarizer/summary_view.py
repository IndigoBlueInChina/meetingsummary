from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, 
                            QComboBox, QFrame, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utils.project_manager import project_manager
import os

class SummaryViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 顶部布局（包含标题和导出按钮）
        top_layout = QHBoxLayout()
        
        # 标题
        title = QLabel("会议纪要预览")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        top_layout.addWidget(title)
        
        # 导出功能
        export_layout = QHBoxLayout()
        export_label = QLabel("导出为：")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown", "PDF", "Word"])
        export_button = QPushButton("导出")
        export_button.setStyleSheet("""
            QPushButton {
                background-color: #33CCFF;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #2CB5E8;
            }
        """)
        
        export_layout.addWidget(export_label)
        export_layout.addWidget(self.format_combo)
        export_layout.addWidget(export_button)
        top_layout.addLayout(export_layout)
        
        main_layout.addLayout(top_layout)
        
        # 中间内容区域
        content_layout = QHBoxLayout()
        
        # 左侧会议记录
        transcript_container = QWidget()
        transcript_layout = QVBoxLayout(transcript_container)
        transcript_label = QLabel("会议记录")
        transcript_label.setFont(QFont("Arial", 16))
        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        transcript_layout.addWidget(transcript_label)
        transcript_layout.addWidget(self.transcript_text)
        content_layout.addWidget(transcript_container)
        
        # 添加垂直分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(line)
        
        # 右侧会议纪要
        summary_container = QWidget()
        summary_layout = QVBoxLayout(summary_container)
        summary_label = QLabel("会议纪要")
        summary_label.setFont(QFont("Arial", 16))
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        summary_layout.addWidget(summary_label)
        summary_layout.addWidget(self.summary_text)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.edit_button = QPushButton("编辑")
        self.edit_button.clicked.connect(self.toggle_edit)
        button_layout.addWidget(self.edit_button)
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_summary)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)
        
        self.export_button_summary = QPushButton("导出")
        self.export_button_summary.clicked.connect(self.export_summary)
        button_layout.addWidget(self.export_button_summary)
        
        summary_layout.addLayout(button_layout)
        
        content_layout.addWidget(summary_container)
        
        main_layout.addLayout(content_layout)
        
        # 底部聊天区域
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setMaximumHeight(150)
        
        self.chat_input = QTextEdit()
        self.chat_input.setMaximumHeight(70)
        self.chat_input.setPlaceholderText("输入您的问题或建议...")
        
        send_button = QPushButton("发送")
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #33CCFF;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #2CB5E8;
            }
        """)
        send_button.clicked.connect(self.send_message)
        
        chat_layout.addWidget(self.chat_history)
        chat_layout.addWidget(self.chat_input)
        chat_layout.addWidget(send_button)
        
        main_layout.addWidget(chat_container)
        
        # 连接信号
        export_button.clicked.connect(self.export_summary)
        
        # 加载最新的总结
        self.load_latest_summary()
        self.load_transcriptfile()
        self.load_summaryfile()
        
    def load_latest_summary(self):
        """加载最新的会议总结"""
        try:
            # 获取总结目录
            summary_dir = project_manager.get_summary_dir()
            if not os.path.exists(summary_dir):
                self.summary_text.setText("未找到会议总结文件")
                return
            
            # 查找最新的总结文件
            summary_files = [f for f in os.listdir(summary_dir) 
                           if f.endswith('_summary.txt')]
            if not summary_files:
                self.summary_text.setText("未找到会议总结文件")
                return
            
            # 获取最新的文件
            latest_file = max(summary_files, 
                            key=lambda x: os.path.getctime(os.path.join(summary_dir, x)))
            summary_path = os.path.join(summary_dir, latest_file)
            
            # 读取总结内容
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_content = f.read()
            
            self.summary_text.setText(summary_content)
            self.current_summary_file = summary_path
            
        except Exception as e:
            print(f"加载总结文件时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.summary_text.setText(f"加载总结文件失败: {str(e)}")
    
    def load_transcriptfile(self):
        """加载转录文件"""
        transcript_file = project_manager.transcript_file
        if not os.path.exists(transcript_file):
            self.transcript_text.setText("未找到转录文件")
            return
        
        file_extension = os.path.splitext(transcript_file)[1].lower()
        if file_extension == ".txt":
            with open(transcript_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.transcript_text.setPlainText(content)
        elif file_extension == ".pdf":
            from PyPDF2 import PdfReader
            with open(transcript_file, 'rb') as f:
                reader = PdfReader(f)
                content = ""
                for page in reader.pages:
                    content += page.extract_text() + '\n'
                self.transcript_text.setPlainText(content)
        elif file_extension == ".docx":
            from docx import Document
            doc = Document(transcript_file)
            content = ""
            for para in doc.paragraphs:
                content += para.text + '\n'
            self.transcript_text.setPlainText(content)
        else:
            self.transcript_text.setText("不支持的文件格式")

    def load_summaryfile(self):
        """加载总结文件"""
        summary_file = project_manager.summary_file
        if not os.path.exists(summary_file):
            self.summary_text.setText("未找到总结文件")
            return
        
        with open(summary_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.summary_text.setPlainText(content)
    
    def toggle_edit(self):
        """切换编辑模式"""
        if self.summary_text.isReadOnly():
            self.summary_text.setReadOnly(False)
            self.edit_button.setText("取消")
            self.save_button.setEnabled(True)
        else:
            self.summary_text.setReadOnly(True)
            self.edit_button.setText("编辑")
            self.save_button.setEnabled(False)
            # 重新加载原内容
            self.load_latest_summary()
    
    def save_summary(self):
        """保存编辑后的总结"""
        try:
            if hasattr(self, 'current_summary_file'):
                with open(self.current_summary_file, 'w', encoding='utf-8') as f:
                    f.write(self.summary_text.toPlainText())
                self.summary_text.setReadOnly(True)
                self.edit_button.setText("编辑")
                self.save_button.setEnabled(False)
        except Exception as e:
            print(f"保存总结文件时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def export_summary(self):
        """导出会议总结"""
        try:
            if hasattr(self, 'current_summary_file'):
                from PyQt6.QtWidgets import QFileDialog
                
                # 获取保存路径
                file_name = QFileDialog.getSaveFileName(
                    self,
                    "导出会议总结",
                    os.path.expanduser("~/Documents"),
                    "文本文件 (*.txt);;Word文档 (*.docx)"
                )
                
                if file_name[0]:
                    if file_name[0].endswith('.txt'):
                        # 直接复制文本文件
                        import shutil
                        shutil.copy2(self.current_summary_file, file_name[0])
                    elif file_name[0].endswith('.docx'):
                        # 转换为Word文档
                        from docx import Document
                        doc = Document()
                        doc.add_heading('会议纪要', 0)
                        doc.add_paragraph(self.summary_text.toPlainText())
                        doc.save(file_name[0])
        except Exception as e:
            print(f"导出总结文件时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def send_message(self):
        """发送消息到LLM并更新聊天历史"""
        message = self.chat_input.toPlainText()
        if message.strip():
            # 添加用户消息到聊天历史
            self.chat_history.append(f"You: {message}")
            self.chat_input.clear()
            
            # TODO: 调用LLM API处理消息
            # response = call_llm_api(message)
            # self.chat_history.append(f"Assistant: {response}")
            
            # TODO: 根据LLM的回复更新会议纪要
            # self.summary_text.setPlainText(updated_summary)
    
    def set_transcript(self, text):
        """设置会议记录文本"""
        self.transcript_text.setPlainText(text)
    
    def set_summary(self, text):
        """设置会议纪要文本"""
        self.summary_text.setPlainText(text)