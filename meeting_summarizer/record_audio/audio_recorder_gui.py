import tkinter as tk
from tkinter import ttk
import threading
from record_audio import list_audio_devices, record_audio
import time

class AudioRecorderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("会议录音")
        self.root.geometry("400x350")
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 设备选择下拉框
        self.devices = list_audio_devices()
        self.device_var = tk.StringVar()
        
        ttk.Label(self.main_frame, text="选择录音设备:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.device_combo = ttk.Combobox(
            self.main_frame, 
            textvariable=self.device_var,
            values=[mic.name for mic in self.devices]
        )
        self.device_combo.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        if self.devices:
            self.device_combo.set(self.devices[0].name)
            
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(
            self.main_frame, 
            textvariable=self.status_var,
            font=("Arial", 12)
        )
        self.status_label.grid(row=2, column=0, sticky=tk.W, pady=20)
        
        # 录音按钮
        self.record_button = ttk.Button(
            self.main_frame,
            text="开始",
            command=self.toggle_recording
        )
        self.record_button.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # 录音状态
        self.is_recording = False
        self.recording_thread = None
        
        # 配置列的权重
        self.main_frame.columnconfigure(0, weight=1)
        
        # 添加录音信息标签
        self.info_frame = ttk.LabelFrame(self.main_frame, text="录音信息", padding="5")
        self.info_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)
        
        self.duration_var = tk.StringVar(value="时长: 00:00:00")
        self.size_var = tk.StringVar(value="大小: 0 B")
        self.disk_var = tk.StringVar(value="磁盘空间: 可用")
        
        ttk.Label(self.info_frame, textvariable=self.duration_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(self.info_frame, textvariable=self.size_var).grid(row=1, column=0, sticky=tk.W)
        ttk.Label(self.info_frame, textvariable=self.disk_var).grid(row=2, column=0, sticky=tk.W)
        
        # 更新定时器
        self.update_timer = None
        
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        try:
            selected_device = self.device_combo.current()
            
            self.is_recording = True
            self.record_button.configure(text="停止")
            self.status_var.set("正在录音...")
            self.device_combo.configure(state="disabled")
            
            # 启动定时更新
            self.update_info()
            
            self.recording_thread = threading.Thread(
                target=self.record_audio_thread,
                args=(selected_device,)
            )
            self.recording_thread.start()
            
        except Exception as e:
            self.status_var.set(f"错误：{str(e)}")
    
    def update_info(self):
        """更新录音信息显示"""
        if self.is_recording:
            # 获取最新状态
            status = record_audio.status.get_status() if hasattr(record_audio, 'status') else None
            
            if status:
                self.duration_var.set(f"时长: {status['duration']}")
                self.size_var.set(f"大小: {status['total_size']}")
                disk_info = status['disk_space']
                self.disk_var.set(f"磁盘空间: 已用 {disk_info['percent']}% ({disk_info['free']} 可用)")
                
                # 磁盘空间警告
                if disk_info['percent'] > 85:
                    self.disk_var.configure(foreground='red')
                
            # 每秒更新一次
            self.update_timer = self.root.after(1000, self.update_info)
    
    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            record_audio.stop_flag = True
            
            # 停止定时更新
            if self.update_timer:
                self.root.after_cancel(self.update_timer)
                self.update_timer = None
            
            self.record_button.configure(text="开始")
            self.status_var.set("正在保存录音...")
            self.device_combo.configure(state="normal")
            
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=5)
                if self.recording_thread.is_alive():
                    self.status_var.set("错误：录音线程无响应")
                    return
    
    def record_audio_thread(self, device_index):
        try:
            result = record_audio(device_index)
            if result:
                wav_files, status = result
                if isinstance(wav_files, list):
                    merged_file = wav_files[-1] if len(wav_files) > 1 else wav_files[0]
                    self.root.after(0, lambda: self.status_var.set(
                        f"录音已保存: {len(wav_files)-1} 个片段\n"
                        f"合并文件: {merged_file}\n"
                        f"总大小: {status['total_size']}"
                    ))
                else:
                    self.root.after(0, lambda: self.status_var.set(f"录音已保存到: {wav_files}"))
            else:
                self.root.after(0, lambda: self.status_var.set("录音保存失败"))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"录音错误: {str(e)}"))
        finally:
            self.root.after(0, self.reset_ui)
    
    def reset_ui(self):
        """重置UI状态"""
        self.is_recording = False
        self.record_button.configure(text="开始")
        self.device_combo.configure(state="normal")
    
    def run(self):
        self.root.mainloop()

def main():
    app = AudioRecorderGUI()
    app.run()

if __name__ == "__main__":
    main() 