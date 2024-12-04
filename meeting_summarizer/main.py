import nltk
import logging
import os
from typing import Optional, Dict, List, Tuple, Any
import json
import requests
import time
from nltk.tokenize import sent_tokenize, word_tokenize
import tiktoken
import re
import docx
from pymupdf4llm import LlamaMarkdownReader
from pathlib import Path
from llm_factory import LLMFactory

# Download required NLTK data
try:
    nltk.download('punkt')
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
        # Common timestamp patterns
        timestamp_patterns = [
            r'\[\d{2}:\d{2}:\d{2}\]',  # [HH:MM:SS]
            r'\d{2}:\d{2}:\d{2}',       # HH:MM:SS
            r'\(\d{2}:\d{2}\)',         # (MM:SS)
        ]
        
        # Check first few lines for timestamp patterns
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
        # Common speaker patterns
        speaker_patterns = [
            r'^[A-Z][a-z]+:',           # Name: 
            r'^Speaker \d+:',           # Speaker 1:
            r'^\[[A-Z][a-z]+\]:',       # [Name]:
        ]
        
        # Split text into initial segments
        lines = text.split('\n')
        segments = []
        current_segment = []
        
        for line in lines:
            # Check if line indicates a new speaker
            is_new_speaker = any(re.match(pattern, line.strip()) for pattern in speaker_patterns)
            
            if is_new_speaker and current_segment:
                segments.append('\n'.join(current_segment))
                current_segment = [line]
            else:
                current_segment.append(line)
        
        # Add the last segment
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
            
            # If adding this segment would exceed the chunk size
            if current_token_count + segment_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_token_count = 0
                
                # Handle segments that are themselves too large
                if segment_tokens > self.max_tokens:
                    # Split into sentences
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
        
        # Add the last chunk
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

class MeetingSummarizer:
    def __init__(self, 
                 provider_type: str = "ollama",
                 provider_config: Dict[str, Any] = None):
        if provider_config is None:
            provider_config = {
                "model_name": "qwen2.5",
                "api_url": "http://localhost:11434"
            }
        
        self.llm = LLMFactory.create_provider(provider_type, **provider_config)
        self.chunker = TranscriptChunker(max_tokens=4000)
        self.logger = logging.getLogger(__name__)

    def generate_chunk_summary(self, chunk: str, chunk_index: int, total_chunks: int) -> Optional[Dict]:
        """
        Generate a summary for a single chunk with context about its position.
        """
        print(f"\n{'='*80}")
        print(f"Processing chunk {chunk_index + 1} of {total_chunks}")
        print(f"Chunk content:\n{chunk[:200]}...") # Show first 200 chars of chunk
        
        context = f"This is part {chunk_index + 1} of {total_chunks} from the meeting transcript."
        
        # Extract time context if available
        first_timestamp_match = re.search(r'\[\d{2}:\d{2}:\d{2}\]|\d{2}:\d{2}:\d{2}|\(\d{2}:\d{2}\)', chunk)
        last_timestamp_match = re.search(r'\[\d{2}:\d{2}:\d{2}\]|\d{2}:\d{2}:\d{2}|\(\d{2}:\d{2}\)', chunk[::-1])
        
        if first_timestamp_match and last_timestamp_match:
            context += f"\nThis section covers from {first_timestamp_match.group()} to {last_timestamp_match.group()}"
        
        prompt = f"""
        {context}
        Please analyze this section and provide:
        1. Main topics discussed in this section
        2. Key decisions made (if any)
        3. Action items mentioned (if any)
        4. Important details that should be connected with other parts
        5. Extract 5-10 key terms/phrases that best represent the content
        6. Identify the primary knowledge domains/fields this content belongs to (e.g., Technology, Business, Healthcare, etc.)

        Format the key terms and domains in JSON format at the end of your response like this:
        ---
        {{"key_terms": ["term1", "term2", "term3", ...], "domains": ["domain1", "domain2", ...]}}
        ---

        Here's the transcript section:
        {chunk}
        """
        
        try:
            response_text = self.llm.generate(prompt)
            if not response_text:
                return None
                
            print("\nresponse_text:")
            print(f"{response_text}\n")     
            
            if "---" in response_text:
                summary_part, json_part = response_text.split("---")[-2:]
            else:
                summary_part = response_text
                json_part = '{"key_terms": [], "domains": []}'
            
            try:
                metadata = json.loads(json_part.strip())
            except:
                metadata = {"key_terms": [], "domains": []}
            
            return {
                "chunk_index": chunk_index,
                "summary": summary_part.strip(),
                "key_terms": metadata["key_terms"],
                "domains": metadata["domains"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error processing chunk {chunk_index}: {str(e)}")
            print(f"Error processing chunk {chunk_index}: {str(e)}")
            return None

    def process_transcript(self, transcript: str) -> Optional[Dict]:
        """
        Process the transcript, handling both timestamped and plain text formats.
        """
        # Split transcript into chunks
        chunks = self.chunker.chunk_transcript(transcript)
        total_chunks = len(chunks)
        
        # Generate summaries for each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            summary = self.generate_chunk_summary(chunk, i, total_chunks)
            if summary:
                chunk_summaries.append(summary)
            time.sleep(1)  # Rate limiting
        
        # Combine all summaries
        if chunk_summaries:
            return self.combine_summaries(chunk_summaries)
        return None

    def combine_summaries(self, chunk_summaries: List[Dict]) -> Optional[Dict]:
        """
        Combine chunk summaries into a final summary.
        """
        # Collect all key terms and domains
        all_key_terms = []
        all_domains = []
        for summary in chunk_summaries:
            all_key_terms.extend(summary.get("key_terms", []))
            all_domains.extend(summary.get("domains", []))
        
        # Remove duplicates while preserving order
        unique_key_terms = list(dict.fromkeys(all_key_terms))
        unique_domains = list(dict.fromkeys(all_domains))
        
        combined_text = "\n\n".join([
            f"Part {summary['chunk_index'] + 1}:\n{summary['summary']}"
            for summary in chunk_summaries
        ])
        
        prompt = f"""
        You are an AI assistant specializing in professional meeting summaries. The input consists of multiple summarized chunks from a meeting. Your task is to combine these into a comprehensive summary with the following sections:

            Knowledge Domains: Analyze and categorize the main fields/domains discussed, explaining their relevance.
            Key Terms Glossary: Organize and explain the key terms by domain/category.
            Key Topics and Agenda: A concise overview of the main topics discussed.
            Discussion Highlights: Summarize the key points under each topic.
            Decisions Made: Outline the decisions and agreements reached.
            Action Items: List actionable tasks, owners, and deadlines if mentioned.
            Questions Raised and Answers: Highlight significant questions and answers.
            Overall Conclusion: Provide a high-level summary.

        Make the final summary professional and well-organized. Keep language same as original transcript. 用中文
        
        Known domains: {unique_domains}
        Known key terms: {unique_key_terms}
        
        Individual summaries:
        {combined_text}
        """
        
        try:
            final_summary = self.llm.generate(prompt)
            if not final_summary:
                return None
                
            return {
                "final_summary": final_summary,
                "metadata": {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "model_used": str(self.llm.__class__.__name__),
                    "number_of_chunks": len(chunk_summaries),
                    "key_terms": unique_key_terms,
                    "domains": unique_domains
                }
            }
        except Exception as e:
            self.logger.error(f"Error generating final summary: {str(e)}")
            print(f"Error generating final summary: {str(e)}")
            return None

def read_file_content(file_path: str) -> str:
    """
    Read content from different file formats (txt, docx, pdf)
    """
    file_ext = Path(file_path).suffix.lower()
    
    try:
        if file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
                
        elif file_ext == '.docx':
            doc = docx.Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            
        elif file_ext == '.pdf':
            md_read = LlamaMarkdownReader()
            result = md_read.load_data(file_path)
            return '\n'.join([doc.text for doc in result])
            
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
            
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {str(e)}")
        raise

def main():
    # Initialize the summarizer
    summarizer = MeetingSummarizer()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('meeting_summarizer.log'),
            logging.StreamHandler()
        ]
    )
    
    # Fix path handling
    input_dir = os.path.join(os.path.dirname(__file__), "..", "transcripts")
    output_dir = os.path.join(os.path.dirname(__file__), "..", "summaries")
    os.makedirs(output_dir, exist_ok=True)
    
    # Update file extension check
    supported_extensions = ('.txt', '.docx', '.pdf')
    
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(supported_extensions):
            try:
                input_path = os.path.join(input_dir, filename)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                base_output_name = f"{Path(filename).stem}_{timestamp}"
                json_output_path = os.path.join(output_dir, f"{base_output_name}_summary.json")
                md_output_path = os.path.join(output_dir, f"{base_output_name}_summary.md")
                
                logging.info(f"Processing file: {filename}")
                transcript = read_file_content(input_path)
                
                summary = summarizer.process_transcript(transcript)
                print("\nsummary:")
                print(f"{summary}\n")               

                if summary:
                    # Save JSON summary
                    with open(json_output_path, 'w', encoding='utf-8') as file:
                        json.dump(summary, file, indent=4, ensure_ascii=False)
                    
                    # Save Markdown summary
                    with open(md_output_path, 'w', encoding='utf-8') as file:
                        file.write(f"# Meeting Summary: {Path(filename).stem}\n\n")
                        file.write(summary['final_summary'])
                    
                    logging.info(f"Successfully saved summaries to {json_output_path} and {md_output_path}")
                
            except Exception as e:
                logging.error(f"Error processing {filename}: {str(e)}")
                continue

if __name__ == "__main__":
    main()
