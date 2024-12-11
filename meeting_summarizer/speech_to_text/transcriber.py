import os
import logging
import traceback
import sys
from funasr import AutoModel
import torch
import numpy as np
import soundfile as sf
from pydub import AudioSegment


### this is example code for other functions call
### 转写文件
## result = transcribe_audio("path/to/audio.wav")

### 转写音频段
## audio_segment = AudioSegment.from_wav("audio.wav")
## result = transcribe_audio(audio_segment)

### SDK模型下载
## from modelscope import snapshot_download
## model_dir = snapshot_download('iic/SenseVoiceSmall')
### 

class SenseVoiceTranscriber:
    def __init__(self, model_id="iic/SenseVoiceSmall"):
        self.logger = logging.getLogger(__name__)
        
        try:
            self.logger.info("Creating ASR model...")
            # 首先确定设备
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            # 创建模型
            self.model = AutoModel(
                model=model_id,
                vad_model="fsmn-vad",  # 添加 VAD 模型
                device=device,  # 传入设备参数
                disable_update=True,
                vad_kwargs={
                    "max_single_segment_time": 30000,
                    "device": device  # VAD模型也需要设备参数
                },
                punc_kwargs={
                    "device": device  # 标点模型也需要设备参数
                }
            )
            self.logger.info(f"Model loaded successfully on {device}")
        except Exception as e:
            self.logger.error(f"Error during model initialization: {str(e)}")
            traceback.print_exc()
            raise

    def load_audio(self, audio_path):
        """加载音频文件并转换为正确的格式"""
        try:
            # 检查文件是否存在
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # 根据文件扩展名处理不同格式
            ext = os.path.splitext(audio_path)[1].lower()
            
            if ext in ['.wav', '.mp3']:
                # 使用 pydub 加载音频
                audio = AudioSegment.from_file(audio_path)
                
                # 转换为单声道
                if audio.channels > 1:
                    audio = audio.set_channels(1)
                
                # 设置采样率为 16kHz
                if audio.frame_rate != 16000:
                    audio = audio.set_frame_rate(16000)
                
                # 转换为 numpy array
                samples = np.array(audio.get_array_of_samples())
                
                # 转换为 float32 并归一化
                samples = samples.astype(np.float32) / 32768.0
                
                return samples
            else:
                raise ValueError(f"Unsupported audio format: {ext}")
                
        except Exception as e:
            self.logger.error(f"Error loading audio file: {str(e)}")
            traceback.print_exc()
            raise

    def clean_transcript(self, text):
        """清理转写文本中的标记"""
        import re
        # 移除语言标记和时间戳
        text = re.sub(r'<\[zh\|.*?\]>', '', text)
        text = re.sub(r'<\[.*?\]>', '', text)
        # 移除多余的空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def transcribe_file(self, audio_path):
        """转写整个音频文件"""
        try:
            # 加载并预处理音频
            audio_data = self.load_audio(audio_path)
            
            # 转写音频
            self.logger.info(f"Transcribing audio file: {audio_path}")
            results = self.model.generate(
                input=audio_data,
                batch_size_s=100,     # 每批处理300秒
                hotword=None,         # 可选的热词列表
                language='auto',      # 自动检测语言
                signal_type='linear', # 线性信号
                use_itn=True,        # 使用反标准化
                mode='offline'       # 离线模式
            )

            # 处理结果
            if results and len(results) > 0:
                # 提取文本并进行后处理
                text = ""
                for result in results:
                    if isinstance(result, dict) and 'text' in result:
                        text += result['text'] + " "
                    elif isinstance(result, str):
                        text += result + " "
                
                # 清理文本
                return self.clean_transcript(text)
            else:
                raise ValueError("No transcription results returned")

        except Exception as e:
            self.logger.error(f"Error in transcription: {str(e)}")
            traceback.print_exc()
            raise

    def transcribe_segment(self, audio_segment):
        """转写音频片段"""
        try:
            # 将 AudioSegment 转换为 numpy array
            audio_array = np.array(audio_segment.get_array_of_samples())
            
            # 如果是立体声，转换为单声道
            if audio_segment.channels == 2:
                audio_array = audio_array.reshape((-1, 2)).mean(axis=1)
            
            # 确保采样率为16k
            if audio_segment.frame_rate != 16000:
                audio_segment = audio_segment.set_frame_rate(16000)
                audio_array = np.array(audio_segment.get_array_of_samples())
            
            # 转换为 float32 并归一化
            audio_array = audio_array.astype(np.float32) / 32768.0
            
            # 转写音频段
            results = self.model.generate(
                input=audio_array,
                batch_size_s=60,
                language='auto',      # 自动检测语言
                signal_type='linear',
                use_itn=True,
                mode='offline'
            )
            
            # 处理结果
            if results and len(results) > 0:
                text = ""
                for result in results:
                    if isinstance(result, dict) and 'text' in result:
                        text += result['text'] + " "
                    elif isinstance(result, str):
                        text += result + " "
                
                # 清理文本
                return self.clean_transcript(text)
            else:
                return ""

        except Exception as e:
            self.logger.error(f"Error in segment transcription: {str(e)}")
            traceback.print_exc()
            return ""

# 全局单例实例
_transcriber = None

def get_transcriber():
    """获取或创建转写器实例"""
    global _transcriber
    if _transcriber is None:
        _transcriber = SenseVoiceTranscriber()
    return _transcriber

def transcribe_audio(audio_input):
    """统一的转写接口"""
    transcriber = get_transcriber()
    
    if isinstance(audio_input, str):
        # 如果输入是文件路径
        return transcriber.transcribe_file(audio_input)
    elif isinstance(audio_input, AudioSegment):
        # 如果输入是音频段
        return transcriber.transcribe_segment(audio_input)
    else:
        raise ValueError("Unsupported input type")

if __name__ == "__main__":
    # 测试代码
    try:
        # 测试文件转写
        test_file = "test.wav"
        if os.path.exists(test_file):
            result = transcribe_audio(test_file)
            print(f"Transcription result: {result}")
    except Exception as e:
        print(f"Test failed: {str(e)}")
        traceback.print_exc()

