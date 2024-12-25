from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QMainWindow, QStackedWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from speech_to_text.transcriber import transcribe_audio
from text_processor.summarizer import generate_summary
from utils.MeetingRecordProject import MeetingRecordProject
import os
from pydub import AudioSegment
import numpy as np
import torch
from utils.flexible_logger import Logger
import traceback



class ProcessingThread(QThread):
    progress_updated = pyqtSignal(str, int)  # 状态信息和进度值
    finished = pyqtSignal(bool, str)  # 成功/失败标志和结果信息
    
    def __init__(self, project_manager):
        super().__init__()
        self.logger = Logger(name="ProcessingThread", console_output=True, file_output=True, log_level="DEBUG")
        self.project_manager = project_manager
        
    def run(self):
        try:
            audio_file_path = self.project_manager.get_audio_filename()
            self.logger.info(f"正在处理音频文件: {audio_file_path}")
            
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"找不到音频文件: {audio_file_path}")
            
            # 加载完整音频文件
            audio = AudioSegment.from_file(audio_file_path)
            # 确保音频是单声道、16kHz采样率
            audio = audio.set_channels(1).set_frame_rate(16000)
            total_length = len(audio)

            # 开始音频转写
            transcript_text = ""
            segment_length = 10000  # 每段10秒

            for i in range(0, total_length, segment_length):
                # 获取音频段
                segment = audio[i:i + segment_length]
                
                # 直接传递 AudioSegment 对象
                segment_text = transcribe_audio(segment)
                transcript_text += segment_text + " "

                progress = min(int((i + segment_length) / total_length * 100), 100)
                self.progress_updated.emit("音频转写中...", progress)

            # 确保转写文本目录存在
            transcript_file = self.project_manager.get_transcript_new_filename()
            os.makedirs(os.path.dirname(transcript_file), exist_ok=True)
            
            # 保存转写文本
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(transcript_text.strip())
                
            self.finished.emit(True, "处理完成")
            self.project_manager.add_transcript(transcript_file)
            
        except Exception as e:
            self.logger.error(f"处理过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.finished.emit(False, str(e))

class StyledProgressBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                text-align: center;
                height: 25px;
                background-color: #F5F5F5;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #33CCFF, stop:1 #3399FF);
                border-radius: 6px;
            }
        """)

class ProcessingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.project_manager = None
        self.processing_thread = None
        self.stop_processing = False
        self.is_processing = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("音频处理")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2C3E50;
            margin-bottom: 10px;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 状态标签
        self.status_label = QLabel("准备开始处理...")
        self.status_label.setStyleSheet("""
            font-size: 16px;
            color: #34495E;
            padding: 10px;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = StyledProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 预计剩余时间标签
        self.time_label = QLabel("等待处理开始...")
        self.time_label.setStyleSheet("""
            color: #7F8C8D;
            font-size: 14px;
            padding: 5px;
        """)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)
        
        # 添加提示信息
        tip_label = QLabel("处理过程中请勿关闭窗口")
        tip_label.setStyleSheet("""
            color: #95A5A6;
            font-style: italic;
            padding: 10px;
        """)
        tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip_label)
        
        layout.addStretch()
        
    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager
        print(f"已设置处理页面的项目管理器: {self.project_manager.project_name}")
        
    def start_processing(self):
        """开始处理音频文件"""
        try:
            print("\n=== 开始音频处理 ===")
            if not self.project_manager:
                raise ValueError("未设置项目管理器")
            
            audio_file = self.project_manager.get_audio_filename()
            if not audio_file:
                raise ValueError("未找到音频文件")
            
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
        
        # 计算预计剩余时间
        remaining_minutes = (100 - progress) // 10
        if remaining_minutes > 0:
            self.time_label.setText(f"预计剩余时间：{remaining_minutes} 分钟")
        else:
            self.time_label.setText("即将完成...")
    
    def processing_finished(self, success, result):
        """Processing completion callback"""
        if success:
            self.status_label.setText("处理完成")
            self.time_label.setText("正在跳转到转写页面...")
            
            try:
                # Get main window
                main_window = self.window()
                if hasattr(main_window, 'switch_to_transcript_view'):
                    # Call main window's switch method
                    main_window.switch_to_transcript_view()
                    print("Requested switch to transcript view")
                else:
                    error_msg = "Main window missing page switch method"
                    print(error_msg)
                    self.status_label.setText(error_msg)
                    
            except Exception as e:
                error_msg = f"Error switching pages: {str(e)}"
                print(error_msg)
                self.status_label.setText(error_msg)
                traceback.print_exc()
        else:
            error_msg = f"处理失败: {result}"
            print(error_msg)
            self.status_label.setText(error_msg)
            self.time_label.setText("请检查错误后重试")
    
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
            self.time_label.setText("等待处理开始...")
            
        except Exception as e:
            print(f"清理处理窗口资源时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()