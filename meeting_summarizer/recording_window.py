import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QComboBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from datetime import datetime
import threading
import time
from audio_recorder.recorder import record_audio, list_audio_devices
from utils.project_manager import project_manager
import os

class RecordingWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 初始化录音相关变量
        self.is_recording = False
        self.is_paused = False
        self.start_time = None
        self.recording_thread = None
        self.available_devices = []
        
        # 创建新项目
        project_manager.create_project()
        print(f"项目目录已创建: {project_manager.get_current_project()}")
        
        self.init_ui()
        self.load_audio_devices()
        
    def init_ui(self):
        # 标题
        title = QLabel("录制会议")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.layout().addWidget(title)

        # 录音时长显示
        self.duration_label = QLabel("录音时长")
        self.duration_label.setFont(QFont("Arial", 12))
        self.layout().addWidget(self.duration_label)

        self.time_label = QLabel("0分钟")
        self.time_label.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.layout().addWidget(self.time_label)

        # 今日录音时长变化
        self.change_label = QLabel("今天 +0%")
        self.change_label.setStyleSheet("color: #00CC00;")
        self.layout().addWidget(self.change_label)

        # 录音设备选择
        device_layout = QHBoxLayout()
        device_label = QLabel("录音设备:")
        device_label.setFont(QFont("Arial", 12))
        
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(200)
        
        # 麦克风控制按钮
        self.mic_button = QPushButton()
        self.mic_button.setFixedSize(32, 32)  # 设置固定大小
        self.mic_button.setCheckable(True)  # 使按钮可切换
        self.mic_button.setChecked(False)  # 默认禁用状态
        self.mic_button.clicked.connect(self.toggle_microphone)
        self.update_mic_button_style()  # 更新按钮样式
        
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(self.mic_button)
        device_layout.addStretch()
        
        self.layout().addLayout(device_layout)

        # 控制按钮
        button_layout = QHBoxLayout()
        
        # 开始/暂停按钮
        self.record_button = QPushButton("开始录音")
        self.record_button.clicked.connect(self.toggle_recording)
        
        # 结束按钮
        self.stop_button = QPushButton("结束")
        self.stop_button.setEnabled(False)  # 初始状态禁用
        self.stop_button.clicked.connect(self.stop_recording)
        
        button_layout.addWidget(self.record_button)
        button_layout.addWidget(self.stop_button)
        
        self.layout().addLayout(button_layout)

        # 状态提示
        self.status_label = QLabel("点击'开始录音'开始会议录制")
        self.status_label.setStyleSheet("color: #666666;")
        self.layout().addWidget(self.status_label)

        # 设置按钮样式
        self.setStyleSheet("""
            QPushButton {
                background-color: #33CCFF;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 15px 30px;
                font-size: 16px;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
            QPushButton#pause {
                background-color: #EEEEEE;
                color: #333333;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
            }
        """)

        # 更新定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_duration)
        self.timer.start(1000)  # 每秒更新一次

    def update_mic_button_style(self):
        """更新麦克风按钮样式"""
        enabled = self.mic_button.isEnabled()
        checked = self.mic_button.isChecked()
        
        # 基础样式
        base_style = """
            QPushButton {
                border: none;
                border-radius: 16px;
                padding: 5px;
            }
        """
        
        if not enabled:
            # 禁用状态
            self.mic_button.setStyleSheet(base_style + """
                QPushButton {
                    background-color: #CCCCCC;
                    background-image: url(assets/mic_disabled.png);
                    background-repeat: no-repeat;
                    background-position: center;
                }
            """)
        elif checked:
            # 启用状态
            self.mic_button.setStyleSheet(base_style + """
                QPushButton {
                    background-color: #33CCFF;
                    background-image: url(assets/mic_on.png);
                    background-repeat: no-repeat;
                    background-position: center;
                }
                QPushButton:hover {
                    background-color: #2CB5E8;
                }
            """)
        else:
            # 禁用状态
            self.mic_button.setStyleSheet(base_style + """
                QPushButton {
                    background-color: #EEEEEE;
                    background-image: url(assets/mic_off.png);
                    background-repeat: no-repeat;
                    background-position: center;
                }
                QPushButton:hover {
                    background-color: #E0E0E0;
                }
            """)

    def toggle_microphone(self):
        """切换麦克风状态"""
        is_enabled = self.mic_button.isChecked()
        self.update_mic_button_style()
        # 更新录音设置
        if hasattr(record_audio, 'use_microphone'):
            record_audio.use_microphone = is_enabled
        print(f"麦克风状态: {'启用' if is_enabled else '禁用'}")

    def load_audio_devices(self):
        """加载可用的录音设备"""
        current_device = self.device_combo.currentText()
        self.device_combo.clear()
        
        try:
            # 获取系统麦克风设备
            devices = list_audio_devices()
            print(f"获取到的设备列表: {devices}")  # 调试信息
            
            # 根据设备名称前缀区分麦克风和其他录音设备
            mic_devices = [dev for dev in devices if str(dev).startswith('<Microphone')]
            other_devices = [dev for dev in devices if str(dev).startswith('<Loopback')]
            
            print(f"麦克风设备: {mic_devices}")  # 调试信息
            print(f"其他录音设备: {other_devices}")  # 调试信息
            
            self.available_devices = other_devices
            
            # 检查是否有麦克风设备
            if mic_devices:
                self.mic_button.setEnabled(True)
            else:
                self.mic_button.setEnabled(False)
                self.mic_button.setChecked(False)
            
            self.update_mic_button_style()
            
            # 添加录音设备到下拉框
            if not self.available_devices:
                self.device_combo.addItem("未找到录音设备")
                self.record_button.setEnabled(False)
                return
                
            for i, dev in enumerate(self.available_devices):
                self.device_combo.addItem(str(dev).split(' ', 1)[1].rstrip('>'), i)
                    
            # 尝试恢复之前选中的设备
            index = self.device_combo.findText(current_device)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)
            
            self.record_button.setEnabled(True)
                
        except Exception as e:
            import traceback
            print(f"加载录音设备失败: {str(e)}")
            print(f"错误详情: {traceback.format_exc()}")  # 打印完整的错误堆栈
            self.device_combo.addItem("加载设备失败")
            self.record_button.setEnabled(False)

    def start_recording(self):
        """开始录音"""
        try:
            if self.is_recording:
                print("录音已在进行中")
                return
            
            # 重置停止标志
            record_audio.stop_flag = False
            record_audio.pause_flag = False
            
            # 获取选中的设备索引
            device_index = self.device_combo.currentIndex()
            if device_index < 0:
                print("错误：未选择录音设备")
                return
            
            # 获取是否启用麦克风
            record_audio.use_microphone = self.mic_button.isChecked()
            
            # 开始录音
            self.is_recording = True
            self.is_paused = False
            self.stop_button.setEnabled(True)
            self.record_button.setText("暂停")
            
            # 创建并启动录音线程
            def record_thread_func():
                try:
                    print("\n=== 开始录音线程 ===")
                    # 开始录音并获取文件路径
                    result = record_audio(
                        device_index=device_index,
                        sample_rate=44100,
                        segment_duration=300,
                        project_dir=None
                    )
                    
                    if isinstance(result, tuple) and len(result) == 2:
                        audio_files, status = result
                        if audio_files and isinstance(audio_files, list):
                            self.audio_files = audio_files
                            print(f"录音完成，文件路径: {audio_files}")
                        else:
                            print("错误：录音函数未返回有效的文件路径列表")
                            self.audio_files = None
                    else:
                        print("错误：录音函数返回值格式不正确")
                        self.audio_files = None
                        
                except Exception as e:
                    print(f"录音线程发生错误: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    self.audio_files = None
                finally:
                    print("录音线程结束")
            
            self.recording_thread = threading.Thread(target=record_thread_func)
            self.recording_thread.start()
            
            # 启动录音时间计时器
            self.start_time = time.time()
            self.timer.start(1000)  # 每秒更新一次
            
        except Exception as e:
            print(f"开始录音时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.is_recording = False
            self.stop_button.setEnabled(False)
            self.record_button.setText("开始录音")

    def stop_recording(self):
        """停止录音"""
        try:
            print("\n=== 停止录音 ===")
            if not self.is_recording:
                print("当前没有录音在进行")
                return

            print("正在停止录音...")
            
            # 禁用按钮，防止重复点击
            self.stop_button.setEnabled(False)
            self.record_button.setEnabled(False)
            
            # 设置停止标志
            record_audio.stop_flag = True
            self.is_recording = False
            self.is_paused = False
            
            # 等待录音线程结束
            if self.recording_thread and self.recording_thread.is_alive():
                print("等待录音线程结束...")
                self.recording_thread.join(timeout=2.0)
                
                if self.recording_thread.is_alive():
                    print("录音线程仍在运行，强制终止...")
                    # 再次等待一小段时间
                    self.recording_thread.join(timeout=1.0)
            
            # 停止计时器
            self.timer.stop()
            
            # 重置录音相关标志
            record_audio.stop_flag = False
            record_audio.pause_flag = False
            record_audio.use_microphone = False
            
            # 检查是否有音频文件生成
            if hasattr(self, 'audio_files') and self.audio_files:
                print(f"录音完成，生成的文件: {self.audio_files}")
                # 切换到音频转文字页面
                QTimer.singleShot(500, self.switch_to_transcribe_page)
            else:
                print("错误：未找到生成的音频文件")
                # 重置按钮状态
                self.stop_button.setEnabled(True)
                self.record_button.setEnabled(True)
                self.record_button.setText("开始录音")
            
        except Exception as e:
            print(f"停止录音时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            # 重置按钮状态
            self.stop_button.setEnabled(True)
            self.record_button.setEnabled(True)
            self.record_button.setText("开始录音")

    def switch_to_transcribe_page(self):
        """切换到音频转文字页面"""
        try:
            if not hasattr(self, 'audio_files') or not self.audio_files:
                print("错误：未找到音频文件")
                return
                
            print(f"找到最新的录音文件: {self.audio_files[0]}")
            
            # 获取主窗口并切换到处理页面
            main_window = self.window()
            if main_window:
                # 设置音频文件路径并切换到处理页面
                main_window.processing_widget.set_audio_file(self.audio_files[0])
                main_window.show_processing_page()
                print(f"已切换到处理页面，音频文件: {self.audio_files[0]}")
            else:
                print("错误：未找到主窗口")
            
        except Exception as e:
            print(f"切换页面时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()

    def toggle_recording(self):
        """切换录音状态"""
        if not self.is_recording:
            self.start_recording()
            self.record_button.setText("暂停")
            self.stop_button.setEnabled(True)
            self.status_label.setText("正在录音...")
        else:
            if not self.is_paused:
                # 暂停录音
                self.is_paused = True
                record_audio.pause_flag = True  # 使用暂停标志而不是停止标志
                self.record_button.setText("继续")
                self.status_label.setText("录音已暂停")
            else:
                # 继续录音
                self.is_paused = False
                record_audio.pause_flag = False  # 重置暂停标志
                record_audio.stop_flag = False  # 确保停止标志也被重置
                self.start_recording()  # 重新开始录音
                self.record_button.setText("暂停")
                self.status_label.setText("录音继续中...")

    def update_duration(self):
        """更新录音时长显示"""
        if self.is_recording and self.start_time and not self.is_paused:
            duration = time.time() - self.start_time
            total_seconds = int(duration)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                time_text = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                time_text = f"{minutes:02d}:{seconds:02d}"
                
            self.time_label.setText(time_text)

    def closeEvent(self, event):
        """窗口关闭时的处理"""
        try:
            print("\n=== 窗口关闭事件触发 ===")
            # 如果正在录音，强制停止
            if self.is_recording:
                print("窗口关闭，强制停止录音...")
                self.is_recording = False
                self.is_paused = False
                record_audio.stop_flag = True
                
                # 等待录音线程结束，但设置超时
                if self.recording_thread:
                    print("等待录音线程结束...")
                    self.recording_thread.join(timeout=2.0)
                    if self.recording_thread.is_alive():
                        print("警告：录音线程未能在规定时间内结束")
            
                # 确保所有标志都被重置
                record_audio.stop_flag = False
                record_audio.pause_flag = False
                record_audio.use_microphone = False
                print("已重置所有录音标志")
                
            else:
                print("窗口关闭时没有活动的录音")
                
        except Exception as e:
            print(f"关闭窗口时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # 调用父类的closeEvent
        super().closeEvent(event)

    def cleanup(self):
        """清理资源并停止所有线程"""
        try:
            print("\n=== 清理录音窗口资源 ===")
            
            # 停止录音
            if self.is_recording:
                print("正在停止录音...")
                record_audio.stop_flag = True
                self.is_recording = False
                self.is_paused = False
                
                # 等待录音线程结束
                if hasattr(self, 'recording_thread') and self.recording_thread and self.recording_thread.is_alive():
                    print("等待录音线程结束...")
                    self.recording_thread.join(timeout=2.0)
                    
                    if self.recording_thread.is_alive():
                        print("录音线程未能正常结束")
            
            # 停止计时器
            if hasattr(self, 'timer'):
                self.timer.stop()
            
            # 重置所有标志
            record_audio.stop_flag = False
            record_audio.pause_flag = False
            record_audio.use_microphone = False
            
            print("录音窗口资源清理完成")
            
        except Exception as e:
            print(f"清理录音窗口资源时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
