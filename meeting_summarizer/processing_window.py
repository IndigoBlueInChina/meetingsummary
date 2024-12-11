from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QMainWindow, QStackedWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from speech_to_text.transcriber import transcribe_audio
from text_processor.summarizer import generate_summary
from utils.project_manager import project_manager
import os
from pydub import AudioSegment
import numpy as np
import torch
import logging
import traceback



class ProcessingThread(QThread):
    progress_updated = pyqtSignal(str, int)  # 状态信息和进度值
    finished = pyqtSignal(bool, str)  # 成功/失败标志和结果信息
    
    def __init__(self, project_manager):
        super().__init__()
        self.project_manager = project_manager
        
    def run(self):
        try:
            # 使用 project_manager 中的实际录音文件路径
            audio_file_path = self.project_manager.record_file
            print(f"正在处理音频文件: {audio_file_path}")
            
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"找不到音频文件: {audio_file_path}")
            
            # 加载完整音频文件
            audio = AudioSegment.from_file(audio_file_path)
            total_length = len(audio)  # 总时长（毫秒）

            # 开始音频转写
            transcript_text = ""
            segment_length = 10000  # 每段音频的长度（毫秒）

            for i in range(0, total_length, segment_length):
                # 获取音频段
                segment = audio[i:i + segment_length]
                
                # 使用 transcribe_audio 处理音频段
                segment_text = transcribe_audio(segment)
                transcript_text += segment_text + " "

                # 更新进度
                progress = min(int((i + segment_length) / total_length * 100), 100)
                self.progress_updated.emit("音频转写中...", progress)  # 发出进度更新信号

            # 确保转写文本目录存在
            os.makedirs(os.path.dirname(self.project_manager.transcript_file), exist_ok=True)
            
            # 保存转写文本
            with open(self.project_manager.transcript_file, "w", encoding="utf-8") as f:
                f.write(transcript_text.strip())
                
            self.finished.emit(True, "处理完成")

        except Exception as e:
            print(f"处理过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.finished.emit(False, str(e))

class ProcessingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.audio_file = None
        self.project_manager = project_manager
        self.init_ui()
        self.processing_thread = None
        self.stop_processing = False
        self.is_processing = False
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 状态标签
        self.status_label = QLabel("准备开始处理...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E0E0E0;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #33CCFF;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 添加进度描述标签
        self.progress_desc_label = QLabel("")
        self.progress_desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_desc_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.progress_desc_label)
        
        layout.addStretch()
        
    def set_audio_file(self, audio_path):
        """设置要处理的音频文件路径"""
        self.audio_file = audio_path
        print(f"设置音频文件: {audio_path}")
        
    def start_processing(self, audio_file=None):
        """开始处理音频文件"""
        try:
            print("\n=== 开始音频处理 ===")
            print(f"Project Manager: {self.project_manager}")
            print(f"Record file: {self.project_manager.record_file if self.project_manager else 'None'}")
            
            if not self.project_manager or not self.project_manager.record_file:
                raise ValueError("未设置有效的音频文件")
            
            # 开始处理线程
            self.processing_thread = ProcessingThread(self.project_manager)
            self.processing_thread.progress_updated.connect(self.update_progress)
            self.processing_thread.finished.connect(self.processing_finished)
            self.processing_thread.start()
            print("处理线程已启动")
            
        except Exception as e:
            print(f"启动处理时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"错误：{str(e)}")
    
    def update_progress(self, status, progress):
        """更新进度信息"""
        self.status_label.setText(status)
        self.progress_bar.setValue(progress)
        if progress < 50:
            self.progress_desc_label.setText("转写进度：{}%".format(progress))
        else:
            self.progress_desc_label.setText("总结进度：{}%".format(progress - 50))
    
    def processing_finished(self, success, result):
        """处理完成的回调函数"""
        if success:
            self.status_label.setText("处理完成")
            # 获取堆叠窗口部件
            stacked_widget = self.parent()
            if isinstance(stacked_widget, QStackedWidget):
                # 获取总结页面并加载内容
                summary_widget = stacked_widget.widget(4)  # 索引4是总结页面
                if summary_widget:
                    # 加载转写文本和会议总结
                    summary_widget.load_transcriptfile()
                    
                    # 切换到总结页面
                    stacked_widget.slide_to_index(4)
                else:
                    self.status_label.setText("无法找到总结页面")
            else:
                self.status_label.setText("无法切换到总结页面")
        else:
            self.status_label.setText(f"处理失败：{result}")
            
    def cleanup(self):
        """清理资源"""
        try:
            if self.processing_thread and self.processing_thread.isRunning():
                self.processing_thread.quit()
                # 给线程一些时间来完成
                if not self.processing_thread.wait(3000):  # 等待3秒
                    self.processing_thread.terminate()
                    self.processing_thread.wait()
            
            # 重置状态
            self.processing_thread = None
            self.stop_processing = False
            self.is_processing = False
            self.progress_bar.setValue(0)
            self.status_label.setText("准备开始处理...")
            self.progress_desc_label.setText("")
            
        except Exception as e:
            print(f"清理处理窗口资源时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()