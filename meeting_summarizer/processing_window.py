from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QMainWindow, QStackedWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from speech_to_text.transcriber import transcribe_audio
from text_processor.summarizer import generate_summary
from utils.project_manager import project_manager
import os

class ProcessingThread(QThread):
    progress_updated = pyqtSignal(str, int)  # 状态信息和进度值
    finished = pyqtSignal(bool, str)  # 成功/失败标志和结果信息
    
    def __init__(self, audio_file):
        super().__init__()
        self.audio_file = audio_file
        
    def run(self):
        try:
            # 第一阶段：音频转写
            self.progress_updated.emit("正在转写音频...", 0)
            
            # 获取文件路径
            transcript_dir = project_manager.get_transcript_dir()
            summary_dir = project_manager.get_summary_dir()
            
            # 生成转写文件名
            transcript_file = os.path.join(
                transcript_dir,
                project_manager.get_transcript_filename(os.path.basename(self.audio_file))
            )
            
            # 确保目录存在
            os.makedirs(os.path.dirname(transcript_file), exist_ok=True)
            
            # 开始音频转写
            transcript_text = transcribe_audio(self.audio_file)
            if not transcript_text:
                raise Exception("音频转写失败：无法获取转写结果")
                
            # 保存转写文本
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(transcript_text)
                
            self.progress_updated.emit("音频转写完成", 50)
            
            # 第二阶段：生成总结
            self.progress_updated.emit("正在生成会议总结...", 50)
            
            # 生成总结文件名
            summary_file = os.path.join(
                summary_dir,
                project_manager.get_summary_filename(os.path.basename(transcript_file))
            )
            
            # 确保目录存在
            os.makedirs(os.path.dirname(summary_file), exist_ok=True)
            
            # 生成会议总结
            summary_text = generate_summary(transcript_text, summary_file)
            if not summary_text:
                raise Exception("会议总结生成失败：无法生成总结")
            
            self.progress_updated.emit("会议总结生成完成", 100)
            self.finished.emit(True, summary_file)
            
        except Exception as e:
            print(f"处理过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.finished.emit(False, str(e))

class ProcessingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.audio_file = None
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
            if not audio_file:
                if not self.audio_file:
                    # 获取最新的音频文件
                    audio_dir = project_manager.get_audio_dir()
                    audio_files = [f for f in os.listdir(audio_dir) 
                                 if f.endswith('.wav') and 'final' in f]
                    if not audio_files:
                        self.status_label.setText("错误：未找到音频文件")
                        return
                        
                    # 选择最新的文件
                    latest_file = max(audio_files, key=lambda x: os.path.getctime(
                        os.path.join(audio_dir, x)))
                    audio_file = os.path.join(audio_dir, latest_file)
                else:
                    audio_file = self.audio_file
            
            # 开始处理线程
            self.processing_thread = ProcessingThread(audio_file)
            self.processing_thread.progress_updated.connect(self.update_progress)
            self.processing_thread.finished.connect(self.processing_finished)
            self.processing_thread.start()
            
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
                    # 加载转写文本
                    transcript_file = os.path.join(project_manager.get_transcript_dir(), 
                                                 os.path.basename(self.audio_file).replace('.wav', '_transcript.txt'))
                    if os.path.exists(transcript_file):
                        with open(transcript_file, 'r', encoding='utf-8') as f:
                            summary_widget.set_transcript(f.read())
                    else:
                        print(f"找不到转写文件: {transcript_file}")
                    
                    # 加载会议总结（注意：总结文件是基于转写文件名生成的）
                    summary_file = os.path.join(project_manager.get_summary_dir(),
                                              os.path.basename(transcript_file).replace('_transcript.txt', '_transcript_summary.txt'))
                    if os.path.exists(summary_file):
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary_widget.set_summary(f.read())
                    else:
                        print(f"找不到总结文件: {summary_file}")
                    
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