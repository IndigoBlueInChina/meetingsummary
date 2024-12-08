import nltk
import logging
import re
from typing import List
import tiktoken
from nltk.tokenize import sent_tokenize

# Download required NLTK data
try:
    nltk.download('punkt')
    nltk.download('punkt_tab')
except Exception as e:
    logging.error(f"Failed to download NLTK data: {str(e)}")

class TranscriptChunker:
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.logger = logging.getLogger(__name__)

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
        """
        speaker_patterns = [
            r'^[A-Z][a-z]+:',           # Name: 
            r'^Speaker \d+:',           # Speaker 1:
            r'^\[[A-Z][a-z]+\]:',       # [Name]:
        ]
        
        lines = text.split('\n')
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
        segments = self.extract_speaker_segments(text)
        chunks = []
        current_chunk = []
        current_token_count = 0
        
        for segment in segments:
            segment_tokens = len(self.tokenizer.encode(segment))
            
            if current_token_count + segment_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_token_count = 0
                
                if segment_tokens > self.max_tokens:
                    sentences = sent_tokenize(segment)
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
        
        return chunks

    def create_timestamped_chunks(self, text: str) -> List[str]:
        """
        Create chunks based on timestamps while preserving time context.
        """
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