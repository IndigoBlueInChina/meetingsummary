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
from config.settings import Settings
import subprocess

# 过滤掉 data discontinuity 警告
warnings.filterwarnings("ignore", category=SoundcardRuntimeWarning, message="data discontinuity in recording")

def check_ffmpeg_available():
    """检查 ffmpeg 是否可用"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def list_audio_devices():
    # 列出所有支持录音的设备（包含虚拟声卡）
    mics = sc.all_microphones(include_loopback=True)
    print("\n可用的音频录制设备:")
    for i, mic in enumerate(mics):
        print(f"{i}: {mic.name}")
    return mics

def merge_audio_files(audio_files, output_file, audio_format="opus", bitrate="64k"):
    """合并多个音频文件，支持不同格式
    
    Args:
        audio_files: 音频文件列表
        output_file: 输出文件路径
        audio_format: 输出格式 (opus, mp3, wav)
        bitrate: 音频比特率 (仅用于压缩格式)
    
    Returns:
        (success: bool, actual_output_file: str) - 成功标志和实际输出文件路径
    """
    try:
        print(f"\n=== 开始合并音频文件 ===")
        print(f"需要合并的文件数量: {len(audio_files)}")
        print(f"输出文件: {output_file}")
        print(f"输出格式: {audio_format}, 比特率: {bitrate}")
        
        if not audio_files:
            print("错误：没有文件需要合并")
            return False, None
        
        # 读取第一个文件作为基础（自动检测格式）
        first_file = audio_files[0]
        if first_file.endswith('.wav'):
            combined = AudioSegment.from_wav(first_file)
        else:
            combined = AudioSegment.from_file(first_file)
        print(f"第一个文件时长: {len(combined)/1000:.2f}秒")
        
        # 逐个添加其他文件
        for i, audio_file in enumerate(audio_files[1:], 1):
            print(f"正在添加第 {i+1} 个文件...")
            if audio_file.endswith('.wav'):
                audio = AudioSegment.from_wav(audio_file)
            else:
                audio = AudioSegment.from_file(audio_file)
            combined += audio
            print(f"当前总时长: {len(combined)/1000:.2f}秒")
        
        # 保存合并后的文件
        print(f"正在保存为 {audio_format} 格式...")
        
        try:
            export_params = {}
            if audio_format in ['opus', 'mp3']:
                export_params['bitrate'] = bitrate
            if audio_format == 'opus':
                export_params['codec'] = 'libopus'
            
            combined.export(output_file, format=audio_format, **export_params)
        except FileNotFoundError:
            # ffmpeg 不可用，回退到 WAV
            print(f"⚠️  警告：无法保存为 {audio_format} 格式（ffmpeg 未安装）")
            print(f"⚠️  自动保存为 WAV 格式")
            # 修改输出文件名为 .wav
            output_file = output_file.rsplit('.', 1)[0] + '.wav'
            combined.export(output_file, format='wav')
        except Exception as e:
            # 其他错误，也回退到 WAV
            print(f"⚠️  警告：格式转换失败: {str(e)}")
            print(f"⚠️  自动保存为 WAV 格式")
            output_file = output_file.rsplit('.', 1)[0] + '.wav'
            combined.export(output_file, format='wav')
        
        # 删除原始分段文件
        print("正在删除临时分段文件...")
        for audio_file in audio_files:
            try:
                os.remove(audio_file)
                print(f"已删除: {os.path.basename(audio_file)}")
            except Exception as e:
                print(f"删除文件 {os.path.basename(audio_file)} 失败: {str(e)}")
        
        print("音频文件合并成功")
        file_size = os.path.getsize(output_file)
        print(f"合并后文件大小: {humanize.naturalsize(file_size)}")
        
        return True, output_file
        
    except Exception as e:
        print(f"\n!!! 合并音频文件时发生错误 !!!")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

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
    
    # 从配置获取音频格式设置
    try:
        settings = Settings()
        audio_format = settings.get("audio", "format") or "opus"
        bitrate = settings.get("audio", "bitrate") or "64k"
    except:
        # 如果无法获取配置，使用默认值
        audio_format = "opus"
        bitrate = "64k"
    
    # 检查 ffmpeg 是否可用（非 WAV 格式需要）
    if audio_format != "wav":
        if not check_ffmpeg_available():
            print(f"\n⚠️  警告：ffmpeg 未安装，无法保存 {audio_format} 格式")
            print("⚠️  自动降级为 WAV 格式（文件较大）")
            print("⚠️  请安装 ffmpeg 以使用压缩格式：")
            print("    1. 运行: .\\install_ffmpeg.ps1")
            print("    2. 或执行: choco install ffmpeg -y")
            print("    3. 重启应用程序\n")
            audio_format = "wav"
    
    print(f"[record_audio] 音频格式: {audio_format}, 比特率: {bitrate}")
    
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
    final_output_files = []  # 跟踪最终输出文件（合并后的文件或原始片段）
    
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
                            sample_rate,
                            audio_format,
                            bitrate
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
                    sample_rate,
                    audio_format,
                    bitrate
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
                    merged_file = f"{base_filename}_merged.{audio_format}"
                    success, actual_file = merge_audio_files(saved_files, merged_file, audio_format, bitrate)
                    if success and actual_file:
                        print(f"[record_audio] 已合并所有录音片段: {actual_file}")
                        final_output_files = [actual_file]
                        return final_output_files, status.get_status()
                    else:
                        print("[record_audio] 合并音频文件失败，返回原始分段文件")
                        final_output_files = saved_files
                        return final_output_files, status.get_status()
                else:
                    print(f"[record_audio] 只有一个录音片段，无需合并")
                    final_output_files = saved_files
                    return final_output_files, status.get_status()
            
            print("[record_audio] 没有录音文件需要处理")
            final_output_files = []
            return final_output_files, status.get_status()
            
    except Exception as e:
        print(f"[record_audio] 录音过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        # 如果已经成功合并文件，返回合并后的文件；否则返回原始片段
        if final_output_files:
            print(f"[record_audio] 错误发生在合并之后，返回已合并的文件: {final_output_files}")
            return final_output_files, status.get_status()
        elif saved_files:
            print(f"[record_audio] 错误发生在合并之前，返回原始片段: {saved_files}")
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

def save_segment(frames, base_filename, segment_count, sample_rate, audio_format="opus", bitrate="64k"):
    """保存单个录音片段，支持多种格式
    
    Args:
        frames: 音频帧数据
        base_filename: 基础文件名
        segment_count: 片段编号
        sample_rate: 采样率
        audio_format: 音频格式 (opus, mp3, wav)
        bitrate: 比特率（用于压缩格式）
    """
    try:
        print(f"[save_segment] 开始保存片段 {segment_count} (格式: {audio_format})...")
        print(f"[save_segment] 输入帧数: {len(frames)}")
        
        # 合并帧
        data = np.concatenate(frames, axis=0)
        print(f"[save_segment] 合并后数据形状: {data.shape}")
        
        # 转换为单声道并标准化
        data = np.mean(data, axis=1)
        print(f"[save_segment] 转换为单声道后形状: {data.shape}")
        data = np.int16(data * 32767)
        
        # 生成片段文件名（扩展名根据格式）
        segment_filename = f"{base_filename}_part{segment_count:03d}.{audio_format}"
        print(f"[save_segment] 保存文件: {segment_filename}")
        
        # 先保存为临时 WAV 文件
        temp_wav = f"{base_filename}_temp_{segment_count}.wav"
        with wave.open(temp_wav, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(data.tobytes())
        
        # 如果需要转换格式
        if audio_format != 'wav':
            try:
                audio = AudioSegment.from_wav(temp_wav)
                export_params = {}
                if audio_format in ['opus', 'mp3']:
                    export_params['bitrate'] = bitrate
                if audio_format == 'opus':
                    export_params['codec'] = 'libopus'
                
                audio.export(segment_filename, format=audio_format, **export_params)
                
                # 删除临时 WAV 文件
                os.remove(temp_wav)
                print(f"[save_segment] 已转换为 {audio_format} 格式")
            except FileNotFoundError as e:
                # ffmpeg 不可用，回退到 WAV
                print(f"[save_segment] ⚠️  警告：无法转换为 {audio_format} 格式（ffmpeg 未安装）")
                print(f"[save_segment] 自动保存为 WAV 格式")
                segment_filename = f"{base_filename}_part{segment_count:03d}.wav"
                os.rename(temp_wav, segment_filename)
            except Exception as e:
                # 其他转换错误，也回退到 WAV
                print(f"[save_segment] ⚠️  警告：格式转换失败: {str(e)}")
                print(f"[save_segment] 自动保存为 WAV 格式")
                segment_filename = f"{base_filename}_part{segment_count:03d}.wav"
                if os.path.exists(temp_wav):
                    os.rename(temp_wav, segment_filename)
        else:
            # 直接重命名 WAV 文件
            os.rename(temp_wav, segment_filename)
        
        file_size = os.path.getsize(segment_filename)
        print(f"[save_segment] 成功保存片段 {segment_count}: {os.path.basename(segment_filename)} ({humanize.naturalsize(file_size)})")
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