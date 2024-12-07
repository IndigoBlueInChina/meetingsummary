import sys
import logging
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog

# 修正导入路径
from meeting_summarizer.audio_recorder.recorder import list_audio_devices, record_audio
from meeting_summarizer.speech_to_text.transcriber import SenseVoiceTranscriber

class MeetingSummarizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("会议记录助手")
        self.root.geometry("800x600")
        
        # 配置日志
        self.setup_logging()
        
        # 创建主界面
        self.create_gui()
        
    def setup_logging(self):
        """配置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def create_gui(self):
        """创建主界面"""
        # 创建标签页控件
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # 创建各功能页面
        self.create_recorder_frame()
        self.create_transcriber_frame()
        
        # 添加状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_recorder_frame(self):
        """创建录音页面"""
        recorder_frame = ttk.Frame(self.notebook)
        self.notebook.add(recorder_frame, text="录音")
        
        # 设备选择
        device_frame = ttk.LabelFrame(recorder_frame, text="录音设备")
        device_frame.pack(fill='x', padx=5, pady=5)
        
        self.device_var = tk.StringVar()
        device_list = list_audio_devices()
        device_menu = ttk.Combobox(device_frame, textvariable=self.device_var)
        device_menu['values'] = device_list
        if device_list:
            device_menu.current(0)
        device_menu.pack(padx=5, pady=5)
        
        # 录音控制
        control_frame = ttk.Frame(recorder_frame)
        control_frame.pack(pady=10)
        
        self.record_button = ttk.Button(control_frame, text="开始录音", command=self.toggle_recording)
        self.record_button.pack(side=tk.LEFT, padx=5)
        
        self.is_recording = False
        
    def create_transcriber_frame(self):
        """创建转写页面"""
        transcriber_frame = ttk.Frame(self.notebook)
        self.notebook.add(transcriber_frame, text="转写")
        
        # 文件选择
        file_frame = ttk.LabelFrame(transcriber_frame, text="音频文件")
        file_frame.pack(fill='x', padx=5, pady=5)
        
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var)
        file_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=5, pady=5)
        
        browse_button = ttk.Button(file_frame, text="浏览", command=self.browse_file)
        browse_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 转写控制
        transcribe_button = ttk.Button(transcriber_frame, text="开始转写", command=self.start_transcribe)
        transcribe_button.pack(pady=10)
        
    def toggle_recording(self):
        """切换录音状态"""
        if not self.is_recording:
            self.record_button.config(text="停止录音")
            self.is_recording = True
            self.status_bar.config(text="正在录音...")
            # 开始录音的逻辑
        else:
            self.record_button.config(text="开始录音")
            self.is_recording = False
            self.status_bar.config(text="录音已停止")
            # 停止录音的逻辑
            
    def browse_file(self):
        """浏览音频文件"""
        filename = filedialog.askopenfilename(
            filetypes=[("音频文件", "*.wav;*.mp3;*.m4a")]
        )
        if filename:
            self.file_path_var.set(filename)
            
    def start_transcribe(self):
        """开始转写"""
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showwarning("警告", "请先选择音频文件")
            return
            
        self.status_bar.config(text="正在转写...")
        # 转写逻辑
        
    def run(self):
        """运行应用程序"""
        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"应用程序运行错误: {str(e)}")
            messagebox.showerror("错误", f"应用程序发生错误：\n{str(e)}")

def main():
    """程序入口点"""
    try:
        root = tk.Tk()
        app = MeetingSummarizerApp(root)
        app.run()
    except Exception as e:
        logging.error(f"程序启动错误: {str(e)}")
        messagebox.showerror("错误", f"程序启动失败：\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()