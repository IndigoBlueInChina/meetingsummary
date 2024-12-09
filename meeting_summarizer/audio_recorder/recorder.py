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
from pathlib import Path
from utils.project_manager import project_manager

def list_audio_devices():
    # 列出所有支持录音的设备（包含虚拟声卡）
    mics = sc.all_microphones(include_loopback=True)
    print("\n可用的音频录制设备:")
    for i, mic in enumerate(mics):
        print(f"{i}: {mic.name}")
    return mics

def get_disk_space(path):
    """获取磁盘空间信息"""
    # 如果路径不存在，使用父目录
    while not os.path.exists(path):
        path = os.path.dirname(path)
    
    disk = psutil.disk_usage(path)
    return {
        'total': humanize.naturalsize(disk.total),
        'used': humanize.naturalsize(disk.used),
        'free': humanize.naturalsize(disk.free),
        'percent': disk.percent
    }

def merge_wav_files(wav_files, output_file):
    """合并多个WAV文件"""
    try:
        if not wav_files:
            print("没有需要合并的文件")
            return False
            
        print(f"\n=== 开始合并音频文件 ===")
        print(f"需要合并的文件数量: {len(wav_files)}")
        print(f"输出文件: {output_file}")
        
        # 使用第一个文件作为基础
        print("读取第一个文件...")
        combined = AudioSegment.from_wav(wav_files[0])
        print(f"第一个文件长度: {len(combined)/1000:.2f}秒")
        
        # 合并其余文件
        for i, wav_file in enumerate(wav_files[1:], 1):
            try:
                print(f"合并第 {i+1}/{len(wav_files)} 个文件: {os.path.basename(wav_file)}")
                segment = AudioSegment.from_wav(wav_file)
                combined += segment
                print(f"当前合并后长度: {len(combined)/1000:.2f}秒")
            except Exception as e:
                print(f"合并文件 {wav_file} 时出错: {str(e)}")
                return False
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 导出合并后的文件
        print("正在导出合并后的文件...")
        combined.export(output_file, format="wav")
        print(f"音频文件合并成功: {output_file}")
        print(f"最终文件长度: {len(combined)/1000:.2f}秒")
        
        # 清理临时文件
        print("\n=== 清理临时文件 ===")
        success = True
        for temp_file in wav_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"已删除临时文件: {os.path.basename(temp_file)}")
            except Exception as e:
                print(f"删除临时文件 {temp_file} 失败: {str(e)}")
                success = False
        
        if success:
            print("\n=== 音频合并完成 ===")
        else:
            print("\n=== 音频合并完成，但部分临时文件清理失败 ===")
        
        return success
        
    except Exception as e:
        print(f"\n!!! 合并音频文件时发生错误 !!!")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

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


def record_audio(device_index=None, sample_rate=44100, segment_duration=300, project_dir=None):

    """
    录制音频并自动分段保存
    """
    print("\n=== 开始录音 ===")
    print(f"指定的项目目录: {project_dir}")
    
    # 确保使用正确的项目目录
    if project_dir is None:
        project_dir = project_manager.get_current_project()
        print(f"使用项目管理器获取目录: {project_dir}")
    
    audio_dir = os.path.join(project_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    print(f"音频保存目录: {audio_dir}")
    
    # 初始化函数属性
    if not hasattr(record_audio, 'stop_flag'):
        record_audio.stop_flag = False
    if not hasattr(record_audio, 'pause_flag'):
        record_audio.pause_flag = False
    if not hasattr(record_audio, 'use_microphone'):
        record_audio.use_microphone = False
   
    # 生成基础文件名（使用时间戳）
    base_filename = os.path.join(audio_dir, f"recording")
    print(f"录音文件基础名: {os.path.basename(base_filename)}")
    
    # 获取录音设备
    mics = sc.all_microphones(include_loopback=True)
    if not mics:
        raise RuntimeError("没有找到可用的录音设备")
    
    mic = mics[device_index] if device_index is not None else mics[0]
    
    # 如果启用麦克风且有可用的麦克风设备，尝试获取麦克风设备
    mic_device = None
    if record_audio.use_microphone:
        try:
            mic_devices = [m for m in sc.all_microphones() if not m.isloopback]
            if mic_devices:
                mic_device = mic_devices[0]
            else:
                print("警告：未找到可用的麦克风设备，将仅录制系统声音")
                record_audio.use_microphone = False
        except Exception as e:
            print(f"警告：获取麦克风设备失败 ({str(e)})，将仅录制系统声音")
            record_audio.use_microphone = False

    print(f"开始录音...")
    print(f"正在录制设备: {mic.name}")
    if mic_device:
        print(f"同时录制麦克风: {mic_device.name}")
    
    recorded_frames = []
    segment_count = 0
    frame_count = 0
    frames_per_segment = int(segment_duration * sample_rate)
    saved_files = []
    
    status = RecordingStatus()
    status.start()
    
    try:
        with mic.recorder(samplerate=sample_rate) as recorder:
            print("录音设备初始化成功")
            mic_recorder = None
            if mic_device:
                try:
                    mic_recorder = mic_device.recorder(samplerate=sample_rate)
                    mic_recorder.__enter__()
                    print("麦克风设备初始化成功")
                except Exception as e:
                    print(f"麦克风初始化失败: {str(e)}")
                    mic_recorder = None
            
            while not record_audio.stop_flag:
                try:
                    if record_audio.pause_flag:
                        time.sleep(0.1)
                        continue
                    
                    # 录制系统声音
                    data = recorder.record(numframes=int(sample_rate * 0.1))
                    
                    # 如果启用麦克风，混合麦克风输入
                    if mic_recorder:
                        try:
                            mic_data = mic_recorder.record(numframes=int(sample_rate * 0.1))
                            data = np.mean([data, mic_data], axis=0)
                        except Exception as e:
                            print(f"麦克风录音错误: {str(e)}")
                            mic_recorder = None
                    
                    recorded_frames.append(data)
                    frame_count += len(data)
                    
                    # 更新状态
                    status.update()
                    
                    # 检查剩余磁盘空间
                    if status.disk_space and status.disk_space['percent'] > 90:
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
                        if segment_file:
                            saved_files.append(segment_file)
                            status.update(segment_file)
                            print(f"已保存录音片段 {segment_count + 1}")
                        recorded_frames = []
                        frame_count = 0
                        segment_count += 1
                        
                except Exception as e:
                    print(f"录音循环中发生错误: {str(e)}")
                    if "Input overflowed" not in str(e):
                        time.sleep(0.1)
                    continue
            
            print("\n=== 录音停止，开始处理数据 ===")
            
            # 关闭麦克风录音器
            if mic_recorder:
                try:
                    mic_recorder.__exit__(None, None, None)
                    print("麦克风录音器已关闭")
                except Exception as e:
                    print(f"关闭麦克风录音器时出错: {str(e)}")
            
            # 保存最后一段录音（如果有）
            if recorded_frames:
                segment_file = save_segment(
                    recorded_frames, 
                    base_filename, 
                    segment_count, 
                    sample_rate
                )
                if segment_file:
                    saved_files.append(segment_file)
                    status.update(segment_file)
                    print(f"已保存最后一段录音")
            
            # 合并所有片段
            if saved_files:
                if len(saved_files) > 1:
                    merged_file = f"{base_filename}_merged.wav"
                    if merge_wav_files(saved_files, merged_file):
                        print(f"已合并所有录音片段: {merged_file}")
                        return [merged_file], status.get_status()
                    else:
                        print("合并音频文件失败，返回原始分段文件")
                        return saved_files, status.get_status()
                else:
                    print(f"只有一个录音片段，无需合并")
                    return saved_files, status.get_status()
            
            print("没有录音文件需要处理")
            return [], status.get_status()
            
    except Exception as e:
        print(f"录音过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        if saved_files:
            return saved_files, status.get_status()
        return [], status.get_status()
    finally:
        # 重置所有标志
        record_audio.stop_flag = False
        record_audio.pause_flag = False
        record_audio.use_microphone = False

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
                device_num = int(input("\n请选择声卡设备编号 (直接回车使用默认设备): ").strip())
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