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
import warnings
from soundcard.mediafoundation import SoundcardRuntimeWarning
from utils.MeetingRecordProject import MeetingRecordProject

# 过滤掉 data discontinuity 警告
warnings.filterwarnings("ignore", category=SoundcardRuntimeWarning, message="data discontinuity in recording")

def list_audio_devices():
    # 列出所有支持录音的设备（包含虚拟声卡）
    mics = sc.all_microphones(include_loopback=True)
    print("\n可用的音频录制设备:")
    for i, mic in enumerate(mics):
        print(f"{i}: {mic.name}")
    return mics

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
        
    def start(self):
        self.start_time = time.time()
        self.duration = 0
        self.saved_segments = 0
        self.total_size = 0
        
    def update(self, new_segment_file=None):
        if self.start_time:
            self.duration = time.time() - self.start_time
            
        if new_segment_file:
            self.saved_segments += 1
            self.total_size += os.path.getsize(new_segment_file)
            
    def get_status(self):
        return {
            'duration': format_time(self.duration),
            'segments': self.saved_segments,
            'total_size': humanize.naturalsize(self.total_size)
        }


def record_audio(device_index=None, sample_rate=44100, segment_duration=300, project_dir=None):
    """
    录制音频并自动分段保存
    """
    print("\n=== [record_audio] 开始录音 ===")
    print(f"[record_audio] 指定的项目目录: {project_dir}")
    print(f"[record_audio] 采样率: {sample_rate}, 分段时长: {segment_duration}秒")
    
    # 确保使用正确的项目目录
    if project_dir is None:
        raise ValueError("[record_audio] 未指定项目目录")
    
    audio_dir = os.path.join(project_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    print(f"[record_audio] 音频保存目录: {audio_dir}")
    
    # 初始化函数属性
    if not hasattr(record_audio, 'stop_flag'):
        record_audio.stop_flag = False
    if not hasattr(record_audio, 'pause_flag'):
        record_audio.pause_flag = False
    if not hasattr(record_audio, 'use_microphone'):
        record_audio.use_microphone = False
    if not hasattr(record_audio, 'current_audio_data'):
        record_audio.current_audio_data = None
        
    print(f"[record_audio] 初始状态 - stop_flag: {record_audio.stop_flag}, pause_flag: {record_audio.pause_flag}, use_microphone: {record_audio.use_microphone}")
    
    # 生成基础文件名（使用时间戳）
    base_filename = os.path.join(audio_dir, f"recording")
    print(f"[record_audio] 录音文件基础名: {os.path.basename(base_filename)}")
    
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
                print("[record_audio] 警告：未找到可用的麦克风设备，将仅录制系统声音")
                record_audio.use_microphone = False
        except Exception as e:
            print(f"[record_audio] 警告：获取麦克风设备失败 ({str(e)})，将仅录制系统声音")
            record_audio.use_microphone = False

    print(f"[record_audio] 开始录音...")
    print(f"[record_audio] 正在录制设备: {mic.name}")
    if mic_device:
        print(f"[record_audio] 同时录制麦克风: {mic_device.name}")
    
    recorded_frames = []
    segment_count = 0
    frame_count = 0
    frames_per_segment = int(segment_duration * sample_rate)
    saved_files = []
    
    print("[record_audio] 初始化状态更新线程...")
    status = RecordingStatus()
    print(f"Before: [record_audio] 状态更新 - duration: {status.duration}, segments: {status.saved_segments}, total_size: {status.total_size}")    
    status.start()
    print(f"After: [record_audio] 状态更新 - duration: {status.duration}, segments: {status.saved_segments}, total_size: {status.total_size}")    

    try:
        with mic.recorder(samplerate=sample_rate, blocksize=4096) as recorder:  
            print("[record_audio] 录音设备初始化成功")
            mic_recorder = None
            last_mic_state = False  # 记录上一次麦克风状态
            last_device = device_index  # 记录上一次设备索引
            
            while not record_audio.stop_flag:
                try:
                    if record_audio.pause_flag:
                        print("[record_audio] 录音已暂停")
                        time.sleep(0.2)
                        continue
                    
                    # 检查并记录 stop_flag 的状态
                    if record_audio.stop_flag:
                        print("[record_audio] 检测到停止信号，准备退出录音循环")
                        break
                    
                    # 减少休眠时间，使线程更快响应停止请求
                    time.sleep(0.01)
                    
                    # 检查设备是否改变
                    if device_index != last_device:
                        print(f"[record_audio] 检测到设备改变: {last_device} -> {device_index}")
                        # 退出当前录音设备的上下文
                        recorder.__exit__(None, None, None)
                        # 获取新的录音设备
                        mics = sc.all_microphones(include_loopback=True)
                        if not mics:
                            print("[record_audio] 错误：没有找到可用的录音设备")
                            record_audio.stop_flag = True
                            break
                        mic = mics[device_index] if device_index is not None else mics[0]
                        print(f"[record_audio] 切换到新设备: {mic.name}")
                        # 初始化新的录音设备
                        recorder = mic.recorder(samplerate=sample_rate, blocksize=4096)
                        recorder.__enter__()
                        last_device = device_index
                        print("[record_audio] 新设备初始化成功")
                    
                    # 检查麦克风状态是否改变
                    current_mic_state = record_audio.use_microphone
                    if current_mic_state != last_mic_state:
                        print(f"[record_audio] 麦克风状态改变: {last_mic_state} -> {current_mic_state}")
                        if current_mic_state:
                            # 麦克风被启用，初始化麦克风
                            try:
                                mic_devices = [m for m in sc.all_microphones() if not m.isloopback]
                                if mic_devices:
                                    mic_device = mic_devices[0]
                                    print(f"[record_audio] 正在初始化麦克风: {mic_device.name}")
                                    mic_recorder = mic_device.recorder(samplerate=sample_rate, blocksize=2048)
                                    mic_recorder.__enter__()
                                    print("[record_audio] 麦克风已启用并初始化成功")
                                else:
                                    print("[record_audio] 警告：未找到可用的麦克风设备")
                                    record_audio.use_microphone = False
                            except Exception as e:
                                print(f"[record_audio] 麦克风初始化失败: {str(e)}")
                                record_audio.use_microphone = False
                        else:
                            # 麦克风被禁用，关闭麦克风
                            if mic_recorder:
                                try:
                                    print("[record_audio] 正在关闭麦克风...")
                                    mic_recorder.__exit__(None, None, None)
                                    mic_recorder = None
                                    print("[record_audio] 麦克风已禁用")
                                except Exception as e:
                                    print(f"[record_audio] 关闭麦克风时出错: {str(e)}")
                        last_mic_state = current_mic_state
                    
                    # 记录当前状态
                    if frame_count % (sample_rate * 2) == 0:  # 每2秒记录一次状态
                        print(f"[record_audio] 当前状态 - 录制时长: {frame_count/sample_rate:.1f}秒, "
                              f"stop_flag: {record_audio.stop_flag}, pause_flag: {record_audio.pause_flag}, "
                              f"use_microphone: {record_audio.use_microphone}")
                    
                    # 减小每次录制的数据量，使线程更容易响应停止请求
                    data = recorder.record(numframes=int(sample_rate * 0.1))
                    
                    # 如果启用麦克风，混合麦克风输入
                    if current_mic_state and mic_recorder:
                        try:
                            mic_data = mic_recorder.record(numframes=int(sample_rate * 0.1))
                            # 将单声道麦克风数据转换为立体声
                            if mic_data.shape[1] == 1 and data.shape[1] == 2:
                                mic_data = np.repeat(mic_data, 2, axis=1)
                            
                            # 确保两个数组形状相同
                            if data.shape == mic_data.shape:
                                # 混合音频，麦克风音量稍微降低以避免失真
                                data = 0.7 * data + 0.3 * mic_data
                            else:
                                print(f"[record_audio] 警告：麦克风数据形状 {mic_data.shape} 与系统音频形状 {data.shape} 不匹配")
                        except Exception as e:
                            print(f"[record_audio] 麦克风录音错误: {str(e)}")
                            mic_recorder = None
                    
                    # 更新实时音频数据用于波形图显示
                    # 将立体声数据转换为单声道用于显示
                    current_data = np.mean(data, axis=1)
                    # 标准化数据到 [-1, 1] 范围
                    max_val = np.max(np.abs(current_data)) if len(current_data) > 0 else 1
                    if max_val > 0:
                        current_data = current_data / max_val
                    record_audio.current_audio_data = current_data
                    
                    recorded_frames.append(data)
                    frame_count += len(data)
                    
                    # 更新状态
                    status.update()
                    
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
                            print(f"[record_audio] 已保存录音片段 {segment_count + 1}")
                        recorded_frames = []
                        frame_count = 0
                        segment_count += 1
                        
                except Exception as e:
                    print(f"[record_audio] 录音循环中发生错误: {str(e)}")
                    if "Input overflowed" not in str(e):
                        time.sleep(0.1)
                    continue
            
            print("\n=== [record_audio] 录音循环结束 ===")
            print(f"[record_audio] 退出原因 - stop_flag: {record_audio.stop_flag}")
            print("[record_audio] 开始清理资源...")
            
            # 关闭麦克风录音器
            if mic_recorder:
                try:
                    print("[record_audio] 正在关闭麦克风录音器...")
                    mic_recorder.__exit__(None, None, None)
                    print("[record_audio] 麦克风录音器已关闭")
                except Exception as e:
                    print(f"[record_audio] 关闭麦克风录音器时出错: {str(e)}")
            
            # 保存最后一段录音（如果有）
            if recorded_frames:
                print(f"[record_audio] 准备保存最后一段录音，数据块数: {len(recorded_frames)}")
                segment_file = save_segment(
                    recorded_frames, 
                    base_filename, 
                    segment_count, 
                    sample_rate
                )
                if segment_file:
                    saved_files.append(segment_file)
                    status.update(segment_file)
                    print(f"[record_audio] 已保存最后一段录音: {segment_file}")
                else:
                    print("[record_audio] 警告：最后一段录音保存失败")
            
            # 合并所有片段
            if saved_files:
                if len(saved_files) > 1:
                    merged_file = f"{base_filename}_merged.wav"
                    if merge_wav_files(saved_files, merged_file):
                        print(f"[record_audio] 已合并所有录音片段: {merged_file}")
                        return [merged_file], status.get_status()
                    else:
                        print("[record_audio] 合并音频文件失败，返回原始分段文件")
                        return saved_files, status.get_status()
                else:
                    print(f"[record_audio] 只有一个录音片段，无需合并")
                    return saved_files, status.get_status()
            
            print("[record_audio] 没有录音文件需要处理")
            return [], status.get_status()
            
    except Exception as e:
        print(f"[record_audio] 录音过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        if saved_files:
            return saved_files, status.get_status()
        return [], status.get_status()
    finally:
        print("[record_audio] 进入 finally 块，准备重置所有标志")
        # 重置所有标志
        record_audio.stop_flag = False
        record_audio.pause_flag = False
        record_audio.use_microphone = False
        record_audio.current_audio_data = None
        print("[record_audio] 所有标志已重置")

def save_segment(frames, base_filename, segment_count, sample_rate):
    """保存单个录音片段"""
    try:
        print(f"[save_segment] 开始保存片段 {segment_count}...")
        print(f"[save_segment] 输入帧数: {len(frames)}")
        
        # 合并帧
        data = np.concatenate(frames, axis=0)
        print(f"[save_segment] 合并后数据形状: {data.shape}")
        
        # 转换为单声道并标准化
        data = np.mean(data, axis=1)
        print(f"[save_segment] 转换为单声道后形状: {data.shape}")
        data = np.int16(data * 32767)
        
        # 生成片段文件名
        segment_filename = f"{base_filename}_part{segment_count:03d}.wav"
        print(f"[save_segment] 保存文件: {segment_filename}")
        
        # 保存为WAV文件
        import wave
        with wave.open(segment_filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(data.tobytes())
        
        print(f"[save_segment] 成功保存片段 {segment_count}: {os.path.basename(segment_filename)}")
        return segment_filename
    except Exception as e:
        print(f"[save_segment] 保存片段 {segment_count} 时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

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