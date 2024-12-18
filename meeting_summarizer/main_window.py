import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QLabel, QFrame, QHBoxLayout, QStackedWidget, 
                            QMessageBox, QDialog)
from PyQt6.QtCore import Qt, QPoint, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QTimer
from PyQt6.QtGui import QIcon, QFont
from utils.MeetingRecordProject import MeetingRecordProject
from recording_window import RecordingWidget
from processing_window import ProcessingWidget
from meeting_summarizer.transcript_window import TranscriptWindow
import os
from history_window import HistoryWindow
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import shutil
from utils.flexible_logger import Logger
from summary_window import SummaryWindow
from datetime import datetime

class SlideStackedWidget(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: white;")

    def slide_to_widget(self, next_widget):
        """Slide to specified widget"""
        if self.currentWidget() == next_widget:
            return

        # Get window width
        width = self.width()
        
        # Set offset direction
        current_index = self.indexOf(self.currentWidget())
        next_index = self.indexOf(next_widget)
        offset = width if current_index > next_index else -width
        
        # Prepare current and next widgets
        current_widget = self.currentWidget()
        self.setCurrentWidget(next_widget)
        
        # Set initial positions
        next_widget.setGeometry(0, 0, width, self.height())
        current_widget.move(0, 0)
        next_widget.move(-offset, 0)
        
        # Create animation group
        anim_group = QParallelAnimationGroup()
        
        # Current widget animation
        anim_current = QPropertyAnimation(current_widget, b"pos")
        anim_current.setDuration(300)
        anim_current.setStartValue(QPoint(0, 0))
        anim_current.setEndValue(QPoint(offset, 0))
        anim_current.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Next widget animation
        anim_next = QPropertyAnimation(next_widget, b"pos")
        anim_next.setDuration(300)
        anim_next.setStartValue(QPoint(-offset, 0))
        anim_next.setEndValue(QPoint(0, 0))
        anim_next.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Add animations to group
        anim_group.addAnimation(anim_current)
        anim_group.addAnimation(anim_next)
        
        # Start animation
        anim_group.start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("会议总结助手")
        self.resize(800, 600)
        
        # Initialize project manager
        self.project_manager = MeetingRecordProject("default_project")
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create stacked widget
        self.stacked_widget = SlideStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create main page
        self.main_page = self.create_main_page()
        
        # Create functional pages
        self.recording_widget = RecordingWidget()
        self.processing_widget = ProcessingWidget()
        self.transcript_widget = TranscriptWindow()
        self.summary_widget = SummaryWindow()
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.main_page)
        self.stacked_widget.addWidget(self.recording_widget)
        self.stacked_widget.addWidget(self.processing_widget)
        self.stacked_widget.addWidget(self.transcript_widget)
        self.stacked_widget.addWidget(self.summary_widget)

        # Ensure main page is shown
        self.stacked_widget.setCurrentWidget(self.main_page)

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        try:
            print("\n=== 正在关闭应用程序 ===")
            
            # 停止录音（如果正在进行）
            if hasattr(self, 'recording_widget'):
                print("正在停止录音...")
                self.recording_widget.cleanup()
            
            # 停止处理（如果正在进行）
            if hasattr(self, 'processing_widget'):
                print("正在停止处理...")
                self.processing_widget.cleanup()
            
            # 等待所有子窗口关闭
            for child in self.findChildren(QWidget):
                if child.isWindow():
                    child.close()
            
            print("应用程序清理完成")
            event.accept()
            
            # 确保程序完全退出
            QTimer.singleShot(500, lambda: os._exit(0))
            
        except Exception as e:
            print(f"关闭应用程序时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            event.accept()
            os._exit(1)

    def create_main_page(self):
        main_page = QWidget()
        layout = QVBoxLayout(main_page)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 添加设置图标
        settings_button = QPushButton()
        settings_button.setIcon(QIcon("assets/settings.png"))
        settings_button.setFixedSize(30, 30)
        settings_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        settings_layout = QHBoxLayout()
        settings_layout.addStretch()
        settings_layout.addWidget(settings_button)
        layout.addLayout(settings_layout)

        # 标题和描述
        title = QLabel("会议总结助手")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(title)

        description = QLabel("欢迎使用会议总结助手，一站式管理您的会议记录。您可以\n录制会议、上传录音或添加文字稿，生成会议纪要。")
        description.setStyleSheet("color: #666666;")
        layout.addWidget(description)

        # 功能按钮
        # 录制会议按钮
        record_button = self.create_feature_button(
            "录制会议",
            "开始录制",
            "assets/record_icon.png"
        )
        record_button.clicked.connect(self.show_recording_page)
        layout.addWidget(record_button)

        # 导入录音或文字稿按钮
        upload_audio_button = self.create_feature_button(
            "导入录音或文字稿",
            "选择录音文件或文字稿文件",
            "assets/upload_audio_icon.png"
        )
        upload_audio_button.clicked.connect(self.import_audio_or_text)  # 直接打开文件选择窗口
        layout.addWidget(upload_audio_button)

        # 查看会议记录按钮
        history_button = self.create_feature_button(
            "查看会议记录",
            "浏览历史会议记录",
            "assets/history_icon.png"
        )
        history_button.clicked.connect(self.show_history_page)
        layout.addWidget(history_button)

        # 添加底部空间
        layout.addStretch()

        return main_page

    def import_audio_or_text(self):
        """打开文件选择对话框"""
        print("打开文件选择对话框-导入录音或文字稿")
        
        # 创建一个 Tkinter 根窗口并隐藏
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口

        # 获取主窗口的位置
        geometry = self.geometry()
        x = geometry.x()
        y = geometry.y()

        # 设置 Tkinter 根窗口位置
        root.geometry(f'400x200+{x+50}+{y+50}')  # 设置对话框位置

        # 打开文件选择对话框
        file_name = filedialog.askopenfilename(
            title="导入录音或文字稿",
            filetypes=[
                ("音频文件", "*.wav;*.mp3;*.m4a"),
                ("文本文件", "*.txt;*.docx;*.pdf")
            ]
        )
        
        if file_name:
            print(f"选择的文件: {file_name}")
            
            # 创建新项目
            project_name = datetime.now().strftime("%Y%m%d_%H%M")
            self.project_manager = MeetingRecordProject(project_name)
            self.project_manager.create()
            
            file_ext = os.path.splitext(file_name)[1].lower()
            
            if file_ext in ['.wav', '.mp3', '.m4a']:
                # 复制音频文件到项目的 audio 目录
                target_file = os.path.join(self.project_manager.audio_dir, os.path.basename(file_name))
                shutil.copy2(file_name, target_file)
                self.project_manager.add_audio(target_file)
                self.processing_widget.set_project_manager(self.project_manager)
                print(f"音频文件已复制到: {target_file}")
                
                # 启动处理窗口
                self.show_processing_page()
            
            elif file_ext in ['.txt', '.docx', '.pdf']:
                # 复制文本文件到项目的 transcript 目录
                target_file = os.path.join(self.project_manager.transcript_dir, os.path.basename(file_name)) 
                shutil.copy2(file_name, target_file)
                self.project_manager.add_transcript(target_file)
                self.transcript_widget.set_project_manager(self.project_manager)  # 使用 set_project_manager 方法
                print(f"文本文件已复制到: {target_file}")
                self.transcript_widget.load_content()  # 加载内容
                
                # 启动总结页面
                self.show_summary_page()
            
            return file_name
        else:
            print("未选择文件")

    def show_recording_page(self):
        """Show recording page"""
        self.stacked_widget.setCurrentWidget(self.recording_widget)

    def show_main_page(self):
        """Return to main page"""
        self.stacked_widget.setCurrentWidget(self.main_page)

    def show_processing_page(self):
        """Show processing page"""
        self.stacked_widget.setCurrentWidget(self.processing_widget)
        self.processing_widget.start_processing()

    def show_summary_page(self):
        """Show summary page"""
        self.stacked_widget.setCurrentWidget(self.transcript_widget)

    def show_history_page(self):
        """显示历史记录页面"""
        self.history_window = HistoryWindow()
        result = self.history_window.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # 获取选中的项目和操作
            selected_project = self.history_window.get_selected_project()
            selected_action = self.history_window.get_selected_action()
            
            if selected_project and selected_action:
                if selected_action == HistoryWindow.ACTION_TRANSCRIBE:
                    # 用户选择转写音频
                    self.processing_widget.project_manager = selected_project
                    self.show_processing_page()
                elif selected_action == HistoryWindow.ACTION_EDIT_SUMMARY:
                    # 用户选择编辑总结
                    self.transcript_widget.project_manager = selected_project
                    self.transcript_widget.load_content()  # 加载内容
                    self.show_summary_page()
        else:
            # 用户取消或关闭窗口，直接返回主页面
            self.show_main_page()

    def create_feature_button(self, title, subtitle, icon_path):
        """创建功能按钮"""
        button = QPushButton()
        button_layout = QVBoxLayout(button)
        button_layout.setContentsMargins(20, 15, 20, 15)

        # 创建水平布局来放置图标和标题
        header_layout = QHBoxLayout()
        
        # 添加图标
        icon_label = QLabel()
        icon_label.setFixedSize(40, 40)
        icon_label.setStyleSheet(f"""
            background-image: url({icon_path});
            background-position: center;
            background-repeat: no-repeat;
        """)
        header_layout.addWidget(icon_label)

        # 添加标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        button_layout.addLayout(header_layout)

        # 添加副标题
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #666666;")
        button_layout.addWidget(subtitle_label)

        # 置按钮样式
        button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                min-height: 100px;
            }
            QPushButton:hover {
                background-color: #F8F8F8;
                border: 1px solid #D0D0D0;
            }
        """)

        return button

    def switch_to_transcript_view(self):
        """Switch to transcript view"""
        try:
            print("\n=== Switching to transcript view ===")
            # Ensure project_manager is set
            if hasattr(self.processing_widget, 'project_manager') and self.processing_widget.project_manager:
                # Set transcript_widget's project_manager
                self.transcript_widget.set_project_manager(self.processing_widget.project_manager)
                # Load content
                self.transcript_widget.load_content()
                # Switch to transcript page using widget reference
                self.stacked_widget.setCurrentWidget(self.transcript_widget)
                print(f"Switched to transcript view, using project: {self.processing_widget.project_manager.project_name}")
            else:
                print("Error: Processing widget's project manager not set")
                
        except Exception as e:
            print(f"Error switching to transcript view: {str(e)}")
            import traceback
            traceback.print_exc()

    def switch_to_summary(self):
        """显示总结对话框"""
        try:
            if not hasattr(self, 'summary_dialog'):
                self.summary_dialog = SummaryWindow(self)
                self.summary_dialog.set_project_manager(self.project_manager)
            
            self.summary_dialog.show_summary()
            self.logger.info("已显示总结对话框")
            
        except Exception as e:
            self.logger.error(f"显示总结对话框失败: {str(e)}")

def main():
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()  # 确保主窗口显示
        sys.exit(app.exec())  # 启动事件循环
    except Exception as e:
        print(f"程序启动时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()