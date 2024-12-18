import nltk
import re
from typing import List
import tiktoken
from nltk.tokenize import sent_tokenize
import os
from pathlib import Path
from utils.flexible_logger import Logger
from utils.language_detector import LanguageDetector

# 创建全局logger实例
logger = Logger(
    name="nltk_setup",
    console_output=True,
    file_output=True,
    log_level="INFO"
)

# 设置本地 NLTK 数据目录（相对于当前文件的位置）
local_nltk_data = os.path.join(os.path.dirname(__file__), 'nltk_data')
if os.path.exists(local_nltk_data):
    nltk.data.path.insert(0, local_nltk_data)  # 优先使用本地数据
    logger.info(f"Using local NLTK data from: {local_nltk_data}")

# 如果本地数据不存在，使用用户目录
user_nltk_data = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "nltk_data")
os.makedirs(user_nltk_data, exist_ok=True)
nltk.data.path.append(user_nltk_data)

def ensure_nltk_data():
    """确保 NLTK 数据可用"""
    try:
        # 检查数据是否已存在
        logger.info("Attempting to find NLTK punkt tokenizer...")
        try:
            nltk.data.find('tokenizers/punkt')
            logger.info("NLTK punkt tokenizer found")
            return True
        except LookupError:
            logger.warning("NLTK punkt tokenizer not found, attempting to download...")
            logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True, raise_on_error=True)
            nltk.download('punkt_tab', quiet=True, raise_on_error=True)
            logger.info("Successfully downloaded NLTK punkt tokenizer")
            return True
    except Exception as e:
        logger.error(f"Failed to initialize NLTK data: {str(e)}")
        logger.error("Will use basic sentence splitting as fallback")
        return False

# 初始化 NLTK 数据
NLTK_AVAILABLE = ensure_nltk_data()

class TranscriptChunker:
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.language_detector = LanguageDetector()
        self.logger = Logger(
            name="chunker",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self.logger.info(f"TranscriptChunker initialized with max_tokens={max_tokens}")
        logger.info("TranscriptChunker instance created.")

    def detect_format(self, text: str) -> str:
        """
        Detect if the transcript has timestamps or is plain text.
        Returns: 'timestamped' or 'plain'
        """
        timestamp_patterns = [
            r'\[\d{2}:\d{2}:\d{2}\]',  # [HH:MM:SS]
            r'\d{2}:\d{2}:\d{2}',       # HH:MM:SS
            r'\(\d{2}:\d{2}\)',         # (MM:SS)
        ]
        
        first_lines = text.split('\n')[:10]
        for line in first_lines:
            for pattern in timestamp_patterns:
                if re.search(pattern, line):
                    return 'timestamped'
        return 'plain'

    def extract_speaker_segments(self, text: str) -> List[str]:
        """
        Split text into segments based on speaker changes or natural breaks.
        If no speaker markers found, split by sentences.
        """
        speaker_patterns = [
            r'^[A-Z][a-z]+:',           # Name: 
            r'^Speaker \d+:',           # Speaker 1:
            r'^\[[A-Z][a-z]+\]:',       # [Name]:
        ]
        
        lines = text.split('\n')
        logger.info(f"Lines: length {len(lines)}")    
        
        # 检查是否有说话人标记
        has_speaker_markers = any(
            any(re.match(pattern, line.strip()) for pattern in speaker_patterns)
            for line in lines
        )
        
        # 如果没有说话人标记，使用句子分割
        if not has_speaker_markers:
            sentences = self.split_into_sentences(text)
            return sentences
        
        # 原有的按说话人分段逻辑
        segments = []
        current_segment = []
        
        for line in lines:
            is_new_speaker = any(re.match(pattern, line.strip()) for pattern in speaker_patterns)
            
            if is_new_speaker and current_segment:
                segments.append('\n'.join(current_segment))
                current_segment = [line]
            else:
                current_segment.append(line)
        
        if current_segment:
            segments.append('\n'.join(current_segment))
        
        return segments

    def create_content_based_chunks(self, text: str, chunk_size: int = 1000) -> List[str]:
        """
        Create chunks based on content when no timestamps are available.
        Uses a combination of speaker changes and semantic breaks.
        """
        logger.info("Starting chunking process...")
        logger.info(f"Creating content-based chunks with size={chunk_size}...")
        segments = self.extract_speaker_segments(text)
        chunks = []
        current_chunk = []
        current_token_count = 0
        
        for segment in segments:
            segment_tokens = len(self.tokenizer.encode(segment))
            # self.logger.info(f"Segment tokens: {segment_tokens}")

            if current_token_count + segment_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_token_count = 0
                
                if segment_tokens > self.max_tokens:
                    sentences = self.split_into_sentences(segment)
                    temp_chunk = []
                    temp_tokens = 0
                    
                    for sentence in sentences:
                        sentence_tokens = len(self.tokenizer.encode(sentence))
                        if temp_tokens + sentence_tokens > self.max_tokens:
                            chunks.append('\n'.join(temp_chunk))
                            temp_chunk = [sentence]
                            temp_tokens = sentence_tokens
                        else:
                            temp_chunk.append(sentence)
                            temp_tokens += sentence_tokens
                    
                    if temp_chunk:
                        chunks.append('\n'.join(temp_chunk))
                else:
                    current_chunk = [segment]
                    current_token_count = segment_tokens
            else:
                current_chunk.append(segment)
                current_token_count += segment_tokens
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        # Check if the first chunk is empty and remove it
        if len(chunks) > 0 and chunks[0].strip() == "":
            chunks.pop(0)
        
        logger.info("Finished creating content-based chunks.")
        return chunks

    def create_timestamped_chunks(self, text: str) -> List[str]:
        """
        Create chunks based on timestamps while preserving time context.
        """
        logger.info("Creating timestamped chunks...")
        timestamp_pattern = r'\[\d{2}:\d{2}:\d{2}\]|\d{2}:\d{2}:\d{2}|\(\d{2}:\d{2}\)'
        segments = re.split(f'(?={timestamp_pattern})', text)
        
        chunks = []
        current_chunk = []
        current_token_count = 0
        
        for segment in segments:
            segment_tokens = len(self.tokenizer.encode(segment))
            
            if current_token_count + segment_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                current_chunk = [segment]
                current_token_count = segment_tokens
            else:
                current_chunk.append(segment)
                current_token_count += segment_tokens
        
        if current_chunk:
            chunks.append(''.join(current_chunk))
        
        logger.info("Finished creating timestamped chunks.")
        return chunks

    def chunk_transcript(self, text: str) -> List[str]:
        """
        Main chunking method that handles both timestamped and plain text formats.
        """
        format_type = self.detect_format(text)
        
        if format_type == 'timestamped':
            self.logger.info("Detected timestamped format - using timestamp-based chunking")
            return self.create_timestamped_chunks(text)
        else:
            self.logger.info("Detected plain text format - using content-based chunking")
            return self.create_content_based_chunks(text)

    def split_into_sentences(self, text: str) -> List[str]:
        """分割文本为句子"""
        if NLTK_AVAILABLE:
            try:
                source_lang = self.language_detector.get_nltk_language_name(text)
                # 直接使用 language_detector 中的 nltk_lang_mapping
                if source_lang in self.language_detector.nltk_lang_mapping.values():
                    self.logger.info(f"Using NLTK sentence tokenizer for {source_lang}")
                    return sent_tokenize(text, language=source_lang)
                else:
                    self.logger.info(f"Language {source_lang} not supported by NLTK, using basic split")
                    
            except Exception as e:
                self.logger.warning(f"NLTK sentence tokenization failed: {str(e)}")
                
        # 如果 NLTK 不可用或失败，使用基本的分割方法
        self.logger.info("Using basic sentence splitting")
        # 使用 positive lookbehind 来保留标点符号
        sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        return [s.strip() for s in sentences if s.strip()]