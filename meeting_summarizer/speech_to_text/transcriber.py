import os
import logging
import traceback
import sys
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import torch

class SenseVoiceTranscriber:
    def __init__(self, model_id="iic/SenseVoiceSmall"):
        self.logger = logging.getLogger(__name__)
        
        try:
            self.logger.info("Creating ASR model...")
            self.model = AutoModel(
                model=model_id,
                vad_model="fsmn-vad",  # 添加 VAD 模型
                vad_kwargs={"max_single_segment_time": 30000},  # VAD 配置
                device='cuda' if torch.cuda.is_available() else 'cpu',
                disable_update=True  # 禁用模型更新检查
            )
            self.logger.info("Model loaded successfully")
        except Exception as e:
            self.logger.error("Error during model initialization:")
            self.logger.error(f"Exception type: {type(e).__name__}")
            self.logger.error(f"Exception message: {str(e)}")
            self.logger.error("Traceback:")
            traceback.print_exc(file=sys.stderr)
            raise

    def transcribe_audio(self, audio_segment):
        try:
            # 处理音频段
            results = self.model.generate(
                input=audio_segment,  # 直接传递 AudioSegment
                cache={},
                language="auto",
                use_itn=True,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15
            )
            
            # 处理转录结果
            if results and len(results) > 0:
                # Apply post-processing
                processed_results = rich_transcription_postprocess(results[0])
                return processed_results
            else:
                raise ValueError("No transcription results returned.")

        except Exception as e:
            logging.error(f"Error in transcribing audio: {str(e)}")
            traceback.print_exc()
            raise

# 全局变量用于缓存转录器实例
_transcriber = None

def get_transcriber():
    global _transcriber
    if _transcriber is None:
        _transcriber = SenseVoiceTranscriber()

def transcribe_audio(audio_file):
    """Wrapper function to handle audio transcription"""
    global _transcriber
    if _transcriber is None:
        _transcriber = SenseVoiceTranscriber()
    return _transcriber.transcribe_audio(audio_file)

def main():
    try:
        # 初始化转录器
        transcriber = get_transcriber()

    except Exception as e:
        logging.error(f"音频转写失败: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()