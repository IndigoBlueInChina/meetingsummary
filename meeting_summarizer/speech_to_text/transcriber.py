import os
from pathlib import Path
import logging
from tqdm import tqdm
import numpy as np
import torch
import traceback
import sys
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

class SenseVoiceTranscriber:
    def __init__(self, model_id="iic/SenseVoiceSmall", cache_dir='./models'):
        self.logger = logging.getLogger(__name__)
        
        try:
            self.logger.info("Creating ASR model...")
            self.model = AutoModel(
                model=model_id,
                vad_model="fsmn-vad",  # 添加 VAD 模型
                vad_kwargs={"max_single_segment_time": 30000},  # VAD 配置
                device='cuda' if torch.cuda.is_available() else 'cpu',
            )
            self.logger.info("Model loaded successfully")
        except Exception as e:
            self.logger.error("Error during model initialization:")
            self.logger.error(f"Exception type: {type(e).__name__}")
            self.logger.error(f"Exception message: {str(e)}")
            self.logger.error("Traceback:")
            traceback.print_exc(file=sys.stderr)
            raise

    def transcribe_audio(self, audio_path, chunk_length_s=30):
        try:
            self.logger.info(f"Processing audio file: {audio_path}")
            
            # 使用 generate 方法进行推理
            results = self.model.generate(
                input=audio_path,
                cache={},
                language="auto",  # 自动检测语言
                use_itn=True,     # 使用标点符号和反向文本归一化
                batch_size_s=60,  # 动态批处理大小
                merge_vad=True,   # 合并 VAD 分段
                merge_length_s=15 # 合并长度
            )
            
            # 处理转录结果
            if results and len(results) > 0:
                # 使用 rich_transcription_postprocess 进行后处理
                text = rich_transcription_postprocess(results[0]["text"])
                return text
            else:
                return ""
            
        except Exception as e:
            self.logger.error("Error during transcription:")
            self.logger.error(f"Exception type: {type(e).__name__}")
            self.logger.error(f"Exception message: {str(e)}")
            self.logger.error("Traceback:")
            traceback.print_exc(file=sys.stderr)
            raise

    def transcribe_directory(self, input_dir, output_dir=None):
        """
        转录目录中的所有音频文件
        :param input_dir: 输入目录路径
        :param output_dir: 输出目录路径（可选）
        """
        input_dir = Path(input_dir)
        if output_dir is None:
            output_dir = input_dir / "transcripts"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        # 支持的音频格式
        audio_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.ogg'}

        for audio_file in input_dir.glob('**/*'):
            if audio_file.suffix.lower() in audio_extensions:
                try:
                    self.logger.info(f"Processing: {audio_file}")

                    # 生成输出文件路径
                    rel_path = audio_file.relative_to(input_dir)
                    output_file = output_dir / f"{rel_path.stem}.txt"
                    output_file.parent.mkdir(parents=True, exist_ok=True)

                    # 转录音频
                    transcript = self.transcribe_audio(str(audio_file))

                    # 保存转录结果
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(transcript)

                    self.logger.info(f"Saved transcript to: {output_file}")

                except Exception as e:
                    self.logger.error(f"Error processing {audio_file}: {str(e)}")
                    continue

# 全局变量用于缓存转录器实例
_transcriber = None

def get_transcriber():
    global _transcriber
    if _transcriber is None:
        _transcriber = SenseVoiceTranscriber()
    return _transcriber

def transcribe_audio(audio_path):
    """
    转录音频文件的包装函数
    :param audio_path: 音频文件路径
    :return: 转录的文本
    """
    try:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
        transcriber = get_transcriber()
        if not transcriber:
            raise RuntimeError("无法初始化转写器")
            
        text = transcriber.transcribe_audio(audio_path)
        if not text or text.strip() == "":
            raise ValueError("转写结果为空")
            
        return text
        
    except Exception as e:
        logging.error(f"音频转写失败: {str(e)}")
        logging.error(f"音频文件: {audio_path}")
        traceback.print_exc()
        raise

def main():
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        # 初始化转录器
        transcriber = SenseVoiceTranscriber()

        # 设置输入输出目录
        input_dir = "transcripts"  # 录音文件目录
        output_dir = "transcripts/text"  # 转录文本输出目录

        # 开始转录
        transcriber.transcribe_directory(input_dir, output_dir)

    except Exception as e:
        logging.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()