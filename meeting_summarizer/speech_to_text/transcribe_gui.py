import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import logging
from pathlib import Path
from transcriber import SenseVoiceTranscriber

class TranscribeGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("语音转文字")
        self.root.geometry("600x500")
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文件选择区域
        self.file_frame = ttk.LabelFrame(self.main_frame, text="文件选择", padding="5")
        self.file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.file_path = tk.StringVar()
        ttk.Entry(self.file_frame, textvariable=self.file_path, width=50).grid(row=0, column=0, padx=5)
        ttk.Button(self.file_frame, text="选择文件", command=self.select_file).grid(row=0, column=1, padx=5)
        
        # 转录选项
        self.options_frame = ttk.LabelFrame(self.main_frame, text="转录选项", padding="5")
        self.options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.options_frame, text="片段长度(秒):").grid(row=0, column=0, padx=5)
        self.chunk_length = tk.StringVar(value="30")
        ttk.Entry(self.options_frame, textvariable=self.chunk_length, width=10).grid(row=0, column=1, padx=5)
        
        # 转录按钮
        self.transcribe_button = ttk.Button(
            self.main_frame,
            text="开始转录",
            command=self.start_transcribe
        )
        self.transcribe_button.grid(row=2, column=0, pady=10)
        
        # 状态显示
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self.main_frame, textvariable=self.status_var).grid(row=3, column=0, pady=5)
        
        # 转录结果显示
        self.result_frame = ttk.LabelFrame(self.main_frame, text="转录结果", padding="5")
        self.result_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.result_text = scrolledtext.ScrolledText(self.result_frame, height=15)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 保存按钮
        self.save_button = ttk.Button(
            self.main_frame,
            text="保存结果",
            command=self.save_result,
            state="disabled"
        )
        self.save_button.grid(row=5, column=0, pady=5)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(4, weight=1)
        
        # 初始化转录器
        self.transcriber = None
        self.transcribe_thread = None
        
    def select_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("音频文件", "*.wav;*.mp3;*.flac;*.m4a;*.ogg"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.file_path.set(file_path)
            
    def start_transcribe(self):
        if not self.file_path.get():
            self.status_var.set("请选择音频文件")
            return
            
        try:
            chunk_length = int(self.chunk_length.get())
        except ValueError:
            self.status_var.set("请输入有效的数值")
            return
            
        self.transcribe_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status_var.set("正在初始化转录器...")
        self.result_text.delete(1.0, tk.END)
        
        def transcribe_thread():
            try:
                if self.transcriber is None:
                    self.transcriber = SenseVoiceTranscriber()
                
                self.status_var.set("正在转录...")
                transcript = self.transcriber.transcribe_audio(
                    self.file_path.get(),
                    chunk_length_s=chunk_length
                )
                
                self.root.after(0, lambda: self.result_text.insert(1.0, transcript))
                self.root.after(0, lambda: self.status_var.set("转录完成"))
                self.root.after(0, lambda: self.save_button.configure(state="normal"))
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.status_var.set(f"转录错误: {str(e)}"))
            finally:
                self.root.after(0, lambda: self.transcribe_button.configure(state="normal"))
        
        self.transcribe_thread = threading.Thread(target=transcribe_thread)
        self.transcribe_thread.start()
    
    def save_result(self):
        if not self.result_text.get(1.0, tk.END).strip():
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.result_text.get(1.0, tk.END))
                self.status_var.set("结果已保存")
            except Exception as e:
                self.status_var.set(f"保存失败: {str(e)}")
    
    def run(self):
        self.root.mainloop()

def main():
    app = TranscribeGUI()
    app.run()

if __name__ == "__main__":
    main()