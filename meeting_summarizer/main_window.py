import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QLabel, QFrame, QHBoxLayout, QStackedWidget, QMessageBox)
from PyQt6.QtCore import Qt, QPoint, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QTimer
from PyQt6.QtGui import QIcon, QFont
from recording_window import RecordingWidget
from upload_window import UploadWidget
from processing_window import ProcessingWidget
from summary_view import SummaryViewWidget
from utils.project_manager import project_manager
import os
from history_window import HistoryWindow

class SlideStackedWidget(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: white;")

    def slide_to_next(self):
        """向左滑动到下一个页面"""
        current_index = self.currentIndex()
        next_index = current_index + 1
        if next_index < self.count():
            self.slide_to_index(next_index)

    def slide_to_prev(self):
        """向右滑动到上一个页面"""
        current_index = self.currentIndex()
        prev_index = current_index - 1
        if prev_index >= 0:
            self.slide_to_index(prev_index)

    def slide_to_index(self, index):
        """滑动到指定索引的页面"""
        if self.currentIndex() == index:
            return

        # 获口宽度
        width = self.width()
        
        # 设置偏移方向
        offset = width if self.currentIndex() > index else -width
        
        # 准备当前页面和目标页面
        current_widget = self.currentWidget()
        self.setCurrentIndex(index)
        next_widget = self.currentWidget()
        
        # 设置初始位置
        next_widget.setGeometry(0, 0, width, self.height())
        current_widget.move(0, 0)
        next_widget.move(-offset, 0)
        
        # 创建动画
        anim_group = QParallelAnimationGroup()
        
        # 当前页面动画
        anim_current = QPropertyAnimation(current_widget, b"pos")
        anim_current.setDuration(300)
        anim_current.setStartValue(QPoint(0, 0))
        anim_current.setEndValue(QPoint(offset, 0))
        anim_current.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 下一页面动画
        anim_next = QPropertyAnimation(next_widget, b"pos")
        anim_next.setDuration(300)
        anim_next.setStartValue(QPoint(-offset, 0))
        anim_next.setEndValue(QPoint(0, 0))
        anim_next.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 添加动画到组
        anim_group.addAnimation(anim_current)
        anim_group.addAnimation(anim_next)
        
        # 开始动画
        anim_group.start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("会议总结助手")
        self.resize(800, 600)
        
        # 确保项目根目录存在
        project_manager.create_project()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建堆叠窗口部件
        self.stacked_widget = SlideStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # 创建主页面
        self.main_page = self.create_main_page()
        
        # 创建各个功能页面
        self.recording_widget = RecordingWidget()
        self.upload_widget = UploadWidget()
        self.processing_widget = ProcessingWidget()
        self.summary_widget = SummaryViewWidget()
        
        # 添加页面到堆叠窗口
        self.stacked_widget.addWidget(self.main_page)        # 主页面
        self.stacked_widget.addWidget(self.recording_widget) # 录音页面
        self.stacked_widget.addWidget(self.upload_widget)    # 上传页面
        self.stacked_widget.addWidget(self.processing_widget) # 处理页面
        self.stacked_widget.addWidget(self.summary_widget)   # 总结页面

        # 确保显示主页面
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

        # 上传录音或文字稿按钮
        upload_audio_button = self.create_feature_button(
            "上传录音或文字稿",
            "选择录音文件或文字稿文件",
            "assets/upload_audio_icon.png"
        )
        upload_audio_button.clicked.connect(self.show_upload_page)
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

    def show_recording_page(self):
        """显示录音页面"""
        self.stacked_widget.slide_to_index(1)  # 切换到录音页面

    def show_main_page(self):
        """返回主页面"""
        self.stacked_widget.slide_to_index(0)  # 切换到主页面

    def show_upload_page(self):
        """显示上传页面"""
        self.stacked_widget.slide_to_index(2)  # 切换到上传页面

    def show_processing_page(self):
        """显示处理页面"""
        self.stacked_widget.slide_to_index(3)  # 切换到处理页面
        self.processing_widget.start_processing()

    def show_summary_page(self):
        """切换到会议纪要预览页面"""
        self.stacked_widget.slide_to_index(4)  # 切换到总结页面

    def show_history_page(self):
        """显示历史记录页面"""
        self.history_window = HistoryWindow()
        self.history_window.show()

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

        # 添加下载图标（如果需要）
        download_icon = QLabel()
        download_icon.setFixedSize(20, 20)
        download_icon.setStyleSheet("""
            background-image: url(path/to/download_icon.png);
            background-position: center;
            background-repeat: no-repeat;
        """)
        header_layout.addWidget(download_icon)

        button_layout.addLayout(header_layout)

        # 添加副标题
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("color: #666666;")
        button_layout.addWidget(subtitle_label)

        # 设置按钮样式
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

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()