import tkinter as tk
from tkinter import ttk
import threading
from record_audio import list_audio_devices, record_audio
import time

class AudioRecorderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("会议录音")
        self.root.geometry("400x250")
        
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
            
            # 在新线程中开始录音
            self.recording_thread = threading.Thread(
                target=self.record_audio_thread,
                args=(selected_device,)
            )
            self.recording_thread.start()
            
        except Exception as e:
            self.status_var.set(f"错误：{str(e)}")
    
    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            record_audio.stop_flag = True  # 设置停止标志
            self.record_button.configure(text="开始")
            self.status_var.set("正在保存录音...")
            self.device_combo.configure(state="normal")
            
            # 等待录音线程结束
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=5)  # 最多等待5秒
                if self.recording_thread.is_alive():
                    self.status_var.set("错误：录音线程无响应")
                    return
    
    def record_audio_thread(self, device_index):
        try:
            wav_files = record_audio(device_index)
            if wav_files:
                if isinstance(wav_files, list):
                    # 多个文件
                    self.root.after(0, lambda: self.status_var.set(
                        f"录音已保存: {len(wav_files)} 个文件\n"
                        f"第一个文件: {wav_files[0]}"
                    ))
                else:
                    # 单个文件
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