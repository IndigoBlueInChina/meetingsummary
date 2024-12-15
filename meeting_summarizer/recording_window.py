import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QComboBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import pyqtgraph as pg
from datetime import datetime
import threading
import time
from audio_recorder.recorder import record_audio, list_audio_devices
from utils.MeetingRecordProject import MeetingRecordProject
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
        self.project_manager = None
        
        # 初始化波形图数据
        self.waveform_data = []
        self.data_index = 0
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_waveform)
        # 不要在初始化时就启动定时器
        # self.plot_timer.start(50)  # 每50ms更新一次波形图
        
        self.init_ui()
        self.load_audio_devices()
        
    def init_ui(self):
        # 标题
        title = QLabel("录制会议")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.layout().addWidget(title)

        # 添加波形图
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')  # 设置白色背景
        self.plot_widget.setMinimumHeight(100)  # 设置最小高度
        self.plot_widget.showGrid(False, False)  # 关闭网格线
        self.plot_widget.getAxis('left').hide()  # 隐藏Y轴
        self.plot_widget.getAxis('bottom').hide()  # 隐藏X轴
        self.plot_curve = self.plot_widget.plot(pen=pg.mkPen(color=(51, 204, 255), width=2))
        self.layout().addWidget(self.plot_widget)
        
        # 录音时长显示
        self.duration_label = QLabel("录音时长")
        self.duration_label.setFont(QFont("Arial", 12))
        self.layout().addWidget(self.duration_label)

        self.time_label = QLabel("0分钟")
        self.time_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.layout().addWidget(self.time_label)

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
        try:
            # 获取所有设备
            devices = list_audio_devices()
            print(f"[RecordingWidget] 获取到的设备列表: {devices}")
            
            # 根据设备名称前缀区分麦克风和其他录音设备
            mic_devices = [dev for dev in devices if str(dev).startswith('<Microphone')]
            other_devices = [dev for dev in devices if str(dev).startswith('<Loopback')]
            
            print(f"[RecordingWidget] 麦克风设备: {mic_devices}")
            print(f"[RecordingWidget] 其他录音设备: {other_devices}")
            
            # 更新可用设备列表
            self.available_devices = other_devices
            self.device_combo.clear()
            
            # 添加录音设备到下拉框
            for i, dev in enumerate(self.available_devices):
                self.device_combo.addItem(f"{i}: {dev.name}")
            
            # 检查是否有麦克风设备
            if mic_devices:
                self.mic_button.setEnabled(True)
                print("[RecordingWidget] 检测到麦克风设备，启用麦克风按钮")
            else:
                self.mic_button.setEnabled(False)
                self.mic_button.setChecked(False)
                print("[RecordingWidget] 未检测到麦克风设备，禁用麦克风按钮")
            
            self.update_mic_button_style()
            
            # 添加设备切换的信号处理
            self.device_combo.currentIndexChanged.connect(self.on_device_changed)
            print("[RecordingWidget] 已加载可用录音设备")
            
        except Exception as e:
            print(f"[RecordingWidget] 加载录音设备时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            self.device_combo.addItem("加载设备失败")
            self.record_button.setEnabled(False)
            
    def on_device_changed(self, index):
        """处理设备切换事件"""
        try:
            print(f"[RecordingWidget] 设备切换: {index}")
            if self.is_recording:
                # 如果正在录音，更新录音设备索引
                record_audio.device_index = index
                print(f"[RecordingWidget] 已更新录音设备索引: {index}")
        except Exception as e:
            print(f"[RecordingWidget] 切换设备时出错: {str(e)}")

    def start_recording(self):
        """开始录音"""
        try:
            if self.is_recording:
                print("录音已在进行中")
                return
            
            # 创建新的 MeetingRecordProject 对象
            project_name = datetime.now().strftime("%Y%m%d_%H%M")
            self.project_manager = MeetingRecordProject(project_name)
            self.project_manager.create()  # 创建项目目录结构
            print(f"项目目录已创建: {self.project_manager.project_dir}")
            
            # 重置波形图数据
            self.waveform_data = []
            self.data_index = 0
            self.plot_curve.setData([])
            
            # 启动波形图更新定时器
            self.plot_timer.start(50)
            print("波形图更新定时器已启动")
            
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
            
            # 开始录音线程
            def record_thread_func():
                try:
                    print("\n=== 开始录音线程 ===")
                    # 使用 project_manager 获取项目目录
                    result = record_audio(
                        device_index=device_index,
                        sample_rate=44100,
                        segment_duration=300,
                        project_dir=self.project_manager.project_dir  # 传入项目目录
                    )
                    
                    if isinstance(result, tuple) and len(result) == 2:
                        audio_files, status = result
                        if audio_files and isinstance(audio_files, list):
                            # 通过 project_manager 设置录音文件
                            self.project_manager.record_file = audio_files[0]
                            self.audio_files = audio_files  # 保留这个用于兼容性
                            print(f"录音完成，文件已保存到项目: {self.project_manager.project_name}")
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

    def update_waveform(self):
        """更新波形图"""
        try:
            if not hasattr(record_audio, 'current_audio_data'):
                return
                
            if not self.is_recording or self.is_paused:
                return
                
            data = record_audio.current_audio_data
            if data is None or len(data) == 0:
                return
                
            # 将数据添加到波形图数据列表
            self.waveform_data.extend(data)
            # 保持最近的1000个数据点
            if len(self.waveform_data) > 1000:
                self.waveform_data = self.waveform_data[-1000:]
            # 更新波形图
            self.plot_curve.setData(self.waveform_data)
        except Exception as e:
            print(f"[RecordingWidget] 更新波形图时发生错误: {str(e)}")

    def stop_recording(self):
        """停止录音"""
        try:
            print("\n=== [RecordingWidget] 停止录音 ===")
            if not self.is_recording:
                print("[RecordingWidget] 当前没有录音在进行")
                return

            # 停止波形图更新定时器
            self.plot_timer.stop()
            print("[RecordingWidget] 波形图更新定时器已停止")

            # 清空波形图
            self.waveform_data = []
            self.plot_curve.setData([])
            print("[RecordingWidget] 已清空波形图")
            
            # 禁用按钮，防止重复点击
            self.stop_button.setEnabled(False)
            self.record_button.setEnabled(False)
            print("[RecordingWidget] 已禁用录音按钮")
            
            # 设置停止标志
            print("[RecordingWidget] 正在设置停止标志...")
            record_audio.stop_flag = True
            self.is_recording = False
            self.is_paused = False
            print(f"[RecordingWidget] 停止标志已设置 - stop_flag: {record_audio.stop_flag}, is_recording: {self.is_recording}, is_paused: {self.is_paused}")
            
            # 等待录音线程结束
            if self.recording_thread and self.recording_thread.is_alive():
                print("[RecordingWidget] 等待录音线程结束...")
                print(f"[RecordingWidget] 线程状态 - 是否存活: {self.recording_thread.is_alive()}, 是否守护线程: {self.recording_thread.daemon}")
                self.recording_thread.join(timeout=2.0)
                
                if self.recording_thread.is_alive():
                    print("[RecordingWidget] 录音线程仍在运行，强制终止...")
                    print(f"[RecordingWidget] 线程状态 - 是否存活: {self.recording_thread.is_alive()}, 是否守护线程: {self.recording_thread.daemon}")
                    # 再次等待一小段时间
                    self.recording_thread.join(timeout=1.0)
                    print(f"[RecordingWidget] 第二次等待后线程状态 - 是否存活: {self.recording_thread.is_alive()}")
            else:
                print("[RecordingWidget] 没有活动的录音线程")
            
            # 停止计时器
            self.timer.stop()
            print("[RecordingWidget] 计时器已停止")
            
            # 重置录音相关标志
            record_audio.stop_flag = False
            record_audio.pause_flag = False
            record_audio.use_microphone = False
            print("[RecordingWidget] 已重置所有录音标志")
            
            # 检查是否有音频文件生成
            if hasattr(self, 'audio_files') and self.audio_files:
                print(f"[RecordingWidget] 录音完成，生成的文件: {self.audio_files}")
                # 切换到音频转文字页面
                QTimer.singleShot(500, self.switch_to_transcribe_page)
            else:
                print("[RecordingWidget] 错误：未找到生成的音频文件")
                # 重置按钮状态
                self.stop_button.setEnabled(True)
                self.record_button.setEnabled(True)
                self.record_button.setText("开始录音")
                print("[RecordingWidget] 已重置按钮状态")
            
        except Exception as e:
            print(f"[RecordingWidget] 停止录音时发生错误: {str(e)}")
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
            if main_window and self.project_manager:
                # 更新 project_manager 的录音文件路径
                self.project_manager.add_audio(self.audio_files[0])
                print(f"已更新项目管理器的录音文件路径: {self.project_manager.get_audio_filename()}")

                # 更新 processing_widget 的 project_manager
                main_window.processing_widget.set_project_manager(self.project_manager)
                
                # 切换到处理页面
                main_window.show_processing_page()  # 切换到处理页面
                print(f"已切换到处理页面，使用项目: {self.project_manager.project_name}")
                
                # 启动转写处理
                QTimer.singleShot(500, main_window.processing_widget.start_processing)
                print("已安排启动转写处理")
            else:
                print("错误：未找到主窗口或 project_manager 未初始化")
        
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
