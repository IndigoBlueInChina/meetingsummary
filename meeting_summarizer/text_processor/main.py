import logging
import os
from typing import Optional, Dict, List, Any
import json
import requests
import time
import re
import docx
from pymupdf4llm import LlamaMarkdownReader
from pathlib import Path
from meeting_summarizer.utils.llm_factory import LLMFactory
from meeting_summarizer.text_processor.chunker import TranscriptChunker
from meeting_summarizer.text_processor.meeting_analyzer import MeetingAnalyzer

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
        self.analyzer = MeetingAnalyzer(self.llm, self.chunker)
        self.logger = logging.getLogger(__name__)
        self.meeting_type = None

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
        
        # Get appropriate prompt based on meeting type
        prompt = self.analyzer.get_summary_prompt(
            self.meeting_type["type"],
            context,
            chunk
        )
        
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
        # First determine meeting type
        self.meeting_type = self.analyzer.determine_meeting_type(transcript)
        self.logger.info(f"Detected meeting type: {self.meeting_type['type']}")
        
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
            final_summary = self.combine_summaries(chunk_summaries)
            if final_summary:
                final_summary["metadata"]["meeting_type"] = self.meeting_type
            return final_summary
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

    def proofread_and_save(self, transcript: str, output_path: str) -> Optional[str]:
        """
        Proofread the transcript and save to file with original format.
        Returns the path to the proofread file if successful.
        """
        if not self.meeting_type:
            # First analyze the meeting to get domains and key terms
            self.meeting_type = self.analyzer.determine_meeting_type(transcript)
        
        # Process transcript to get all key terms and domains
        result = self.process_transcript(transcript)
        if not result:
            self.logger.error("Failed to process transcript for proofreading")
            return None
        
        # Get all unique domains and key terms
        domains = result["metadata"].get("domains", [])
        key_terms = result["metadata"].get("key_terms", [])
        
        # Proofread the transcript
        proofread_text = self.analyzer.proofread_transcript(transcript, domains, key_terms)
        
        # Determine output path for proofread version
        output_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]
        ext = os.path.splitext(output_path)[1]
        proofread_path = os.path.join(output_dir, f"{base_name}_proofread{ext}")
        
        try:
            # Save proofread text with original format
            with open(proofread_path, 'w', encoding='utf-8') as f:
                f.write(proofread_text)
            self.logger.info(f"Saved proofread transcript to {proofread_path}")
            return proofread_path
        except Exception as e:
            self.logger.error(f"Error saving proofread transcript: {str(e)}")
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
                
                # Define output paths
                json_output_path = os.path.join(output_dir, f"{base_output_name}_summary.json")
                md_output_path = os.path.join(output_dir, f"{base_output_name}_summary.md")
                proofread_output_path = os.path.join(output_dir, f"{base_output_name}_proofread{Path(filename).suffix}")
                
                logging.info(f"Processing file: {filename}")
                transcript = read_file_content(input_path)
                
                # Step 1: Generate summary
                summary = summarizer.process_transcript(transcript)
                
                if summary:
                    # Save summary files
                    with open(json_output_path, 'w', encoding='utf-8') as file:
                        json.dump(summary, file, indent=4, ensure_ascii=False)
                    
                    with open(md_output_path, 'w', encoding='utf-8') as file:
                        file.write(f"# Meeting Summary: {Path(filename).stem}\n\n")
                        file.write(summary['final_summary'])
                    
                    logging.info(f"Successfully saved summaries to {json_output_path} and {md_output_path}")
                    
                    # Step 2: Generate proofread version using the domains and key terms from summary
                    proofread_path = summarizer.proofread_and_save(transcript, proofread_output_path)
                    if proofread_path:
                        logging.info(f"Successfully saved proofread version to {proofread_path}")
                    
                    logging.info(f"Successfully processed {filename}")
                else:
                    logging.error(f"Failed to generate summary for {filename}")
                
            except Exception as e:
                logging.error(f"Error processing {filename}: {str(e)}")
                continue

if __name__ == "__main__":
    main()
