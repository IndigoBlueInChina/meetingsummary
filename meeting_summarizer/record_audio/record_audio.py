import soundcard as sc
import numpy as np
import os
from datetime import datetime
from pydub import AudioSegment
from pydub.utils import make_chunks
import tempfile
import wave
import time

def list_audio_devices():
    # 列出所有支持录音的设备（包含虚拟声卡）
    mics = sc.all_microphones(include_loopback=True)
    print("\n可用的音频录制设备:")
    for i, mic in enumerate(mics):
        print(f"{i}: {mic.name}")
    return mics

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
    
    try:
        with mic.recorder(samplerate=sample_rate) as recorder:
            while not record_audio.stop_flag:
                # 每次录制一小段（0.1秒）
                data = recorder.record(numframes=int(sample_rate * 0.1))
                recorded_frames.append(data)
                frame_count += len(data)
                
                # 检查是否需要保存当前段
                if frame_count >= frames_per_segment:
                    segment_file = save_segment(
                        recorded_frames, 
                        base_filename, 
                        segment_count, 
                        sample_rate
                    )
                    saved_files.append(segment_file)
                    recorded_frames = []  # 清空缓存
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
        
        print(f"录音完成，共保存 {len(saved_files)} 个片段")
        return saved_files
        
    except Exception as e:
        print(f"录音错误: {str(e)}")
        return None
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