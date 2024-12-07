import soundcard as sc
import numpy as np
import os
from datetime import datetime
from pydub import AudioSegment
from pydub.utils import make_chunks
import tempfile
import wave
import time
import psutil
import humanize

def list_audio_devices():
    # 列出所有支持录音的设备（包含虚拟声卡）
    mics = sc.all_microphones(include_loopback=True)
    print("\n可用的音频录制设备:")
    for i, mic in enumerate(mics):
        print(f"{i}: {mic.name}")
    return mics

def get_disk_space(path):
    """获取磁盘空间信息"""
    disk = psutil.disk_usage(path)
    return {
        'total': humanize.naturalsize(disk.total),
        'used': humanize.naturalsize(disk.used),
        'free': humanize.naturalsize(disk.free),
        'percent': disk.percent
    }

def merge_wav_files(wav_files, output_file):
    """合并多个WAV文件"""
    if not wav_files:
        return None
        
    try:
        # 读取第一个文件作为基础
        combined = AudioSegment.from_wav(wav_files[0])
        
        # 添加其余文件
        for wav_file in wav_files[1:]:
            audio = AudioSegment.from_wav(wav_file)
            combined += audio
            
        # 导出合并后的文件
        combined.export(output_file, format="wav")
        return output_file
    except Exception as e:
        print(f"合并音频文件失败: {str(e)}")
        return None

def format_time(seconds):
    """格式化时间为 HH:MM:SS"""
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

class RecordingStatus:
    def __init__(self):
        self.start_time = None
        self.duration = 0
        self.saved_segments = 0
        self.total_size = 0
        self.disk_space = None
        
    def start(self):
        self.start_time = time.time()
        self.duration = 0
        self.saved_segments = 0
        self.total_size = 0
        self.update_disk_space()
        
    def update(self, new_segment_file=None):
        if self.start_time:
            self.duration = time.time() - self.start_time
            
        if new_segment_file:
            self.saved_segments += 1
            self.total_size += os.path.getsize(new_segment_file)
            self.update_disk_space()
            
    def update_disk_space(self):
        self.disk_space = get_disk_space('transcripts')
        
    def get_status(self):
        return {
            'duration': format_time(self.duration),
            'segments': self.saved_segments,
            'total_size': humanize.naturalsize(self.total_size),
            'disk_space': self.disk_space
        }

def record_audio(device_index=None, sample_rate=44100, segment_duration=300):  # 默认5分钟一段
    """
    录制音频并自动分段保存
    :param device_index: 录音设备索引
    :param sample_rate: 采样率
    :param segment_duration: 每段录音的时长（秒）
    """
    # 确保输出目录存在
    os.makedirs('transcripts', exist_ok=True)
    
    # 生成基础文件名（使用时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"transcripts/recording_{timestamp}"
    
    # 获取默认扬声器或指定扬声器
    mics = sc.all_microphones(include_loopback=True)
    if not mics:
        raise RuntimeError("没有找到可用的录音设备")
    
    mic = mics[device_index] if device_index is not None else mics[0]
    
    # 重置停止标志
    record_audio.stop_flag = False
    
    print(f"开始录音...")
    print(f"正在录制设备: {mic.name}")
    
    recorded_frames = []
    segment_count = 0
    frame_count = 0
    frames_per_segment = int(segment_duration * sample_rate)  # 每段的帧数
    saved_files = []
    
    status = RecordingStatus()
    status.start()
    
    try:
        with mic.recorder(samplerate=sample_rate) as recorder:
            while not record_audio.stop_flag:
                data = recorder.record(numframes=int(sample_rate * 0.1))
                recorded_frames.append(data)
                frame_count += len(data)
                
                # 更新状态
                status.update()
                
                # 检查剩余磁盘空间
                if status.disk_space['percent'] > 90:  # 磁盘使用超过90%
                    print("警告：磁盘空间不足")
                    record_audio.stop_flag = True
                    break
                
                # 检查是否需要保存当前段
                if frame_count >= frames_per_segment:
                    segment_file = save_segment(
                        recorded_frames, 
                        base_filename, 
                        segment_count, 
                        sample_rate
                    )
                    saved_files.append(segment_file)
                    status.update(segment_file)  # 更新状态
                    recorded_frames = []
                    frame_count = 0
                    segment_count += 1
                    print(f"已保存录音片段 {segment_count}")
            
            # 保存最后一段
            if recorded_frames:
                segment_file = save_segment(
                    recorded_frames, 
                    base_filename, 
                    segment_count, 
                    sample_rate
                )
                saved_files.append(segment_file)
                status.update(segment_file)
        
        # 合并所有片段
        if len(saved_files) > 1:
            merged_file = f"{base_filename}_merged.wav"
            if merge_wav_files(saved_files, merged_file):
                saved_files.append(merged_file)
        
        print(f"录音完成，共保存 {len(saved_files)} 个片段")
        return saved_files, status.get_status()
        
    except Exception as e:
        print(f"录音错误: {str(e)}")
        return None, None
    finally:
        record_audio.stop_flag = False

def save_segment(frames, base_filename, segment_count, sample_rate):
    """保存单个录音片段"""
    # 合并帧
    data = np.concatenate(frames, axis=0)
    # 转换为单声道并标准化
    data = np.mean(data, axis=1)
    data = np.int16(data * 32767)
    
    # 生成片段文件名
    segment_filename = f"{base_filename}_part{segment_count:03d}.wav"
    
    # 保存为WAV文件
    with wave.open(segment_filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())
    
    return segment_filename

# 添加停止标志
record_audio.stop_flag = False

if __name__ == "__main__":
    print("开始运行录音程序...")
    try:
        print("正在检测可用音频设备...")
        # 列出可用设备
        available_devices = list_audio_devices()
        
        if not available_devices:
            print("没有检测到可用的音频设备。")
            exit(1)
        
        # 选择输入设备
        device_index = None
        if len(available_devices) > 1:
            try:
                device_num = int(input("\n请选择声卡设备编号 (直接回��使用默认设备): ").strip())
                if 0 <= device_num < len(available_devices):
                    device_index = device_num
            except ValueError:
                print("使用默认设备")
        
        # 开始录音
        record_audio(device_index)
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("程序结束") 