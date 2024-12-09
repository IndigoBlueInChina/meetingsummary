from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor
import numpy as np

class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.points = []
        self.max_points = 100  # 显示的数据点数量
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_waveform)
        self.timer.start(50)  # 每50ms更新一次
        self.amplitude = 0
        
    def update_amplitude(self, value):
        """更新音频振幅值"""
        self.amplitude = value
        
    def update_waveform(self):
        """更新波形图数据"""
        if len(self.points) >= self.max_points:
            self.points.pop(0)
        
        # 生成随机波形数据，实际使用时应该用真实的音频数据
        new_point = self.amplitude * np.random.random()
        self.points.append(new_point)
        self.update()
        
    def paintEvent(self, event):
        """绘制波形图"""
        if not self.points:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 设置波形图的颜色和线条样式
        pen = QPen(QColor("#33CCFF"))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # 计算绘图区域
        width = self.width()
        height = self.height()
        center_y = height / 2
        
        # 绘制波形
        path_width = width / (len(self.points) - 1) if len(self.points) > 1 else width
        for i in range(len(self.points) - 1):
            x1 = i * path_width
            x2 = (i + 1) * path_width
            y1 = center_y + (self.points[i] * height / 2)
            y2 = center_y + (self.points[i + 1] * height / 2)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            
    def start(self):
        """开始更新波形图"""
        self.timer.start()
        
    def stop(self):
        """停止更新波形图"""
        self.timer.stop()
        self.points.clear()
        self.update()
