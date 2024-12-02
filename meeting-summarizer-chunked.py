import logging
import os
from typing import Optional, Dict, List
import json
import requests
import time
from nltk.tokenize import sent_tokenize
import tiktoken

class MeetingSummarizer:
    def __init__(self, 
                 model_name: str = "llama2", 
                 api_url: str = "http://localhost:11434",
                 max_tokens: int = 4000):
        """
        Initialize the meeting summarizer with chunking capability.
        
        Args:
            model_name (str): Name of the Ollama model to use
            api_url (str): URL of the Ollama API
            max_tokens (int): Maximum tokens per chunk
        """
        self.model_name = model_name
        self.api_url = api_url
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)
        
        # Initialize tokenizer for counting tokens
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.
        """
        return len(self.tokenizer.encode(text))

    def chunk_transcript(self, text: str) -> List[str]:
        """
        Split the transcript into smaller chunks based on token limit.
        
        Args:
            text (str): Full transcript text
            
        Returns:
            List[str]: List of text chunks
        """
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Split into sentences first
        sentences = sent_tokenize(text)
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if current_length + sentence_tokens > self.max_tokens:
                # Save current chunk if it's not empty
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_length += sentence_tokens
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        self.logger.info(f"Split transcript into {len(chunks)} chunks")
        return chunks

    def generate_chunk_summary(self, chunk: str, chunk_index: int) -> Optional[Dict]:
        """
        Generate a summary for a single chunk.
        
        Args:
            chunk (str): Text chunk to summarize
            chunk_index (int): Index of the chunk
            
        Returns:
            Optional[Dict]: Dictionary containing the chunk summary
        """
        prompt = f"""
        This is part {chunk_index + 1} of a longer meeting transcript. Please analyze this section and provide:
        1. Main topics discussed in this section
        2. Key decisions made (if any)
        3. Action items mentioned (if any)
        4. Important details that should be connected with other parts
        
        Here's the transcript section:
        {chunk}
        """
        
        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "chunk_index": chunk_index,
                "summary": response.json()["response"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error processing chunk {chunk_index}: {str(e)}")
            return None

    def combine_summaries(self, chunk_summaries: List[Dict]) -> Optional[Dict]:
        """
        Combine multiple chunk summaries into a final summary.
        
        Args:
            chunk_summaries (List[Dict]): List of chunk summaries
            
        Returns:
            Optional[Dict]: Final combined summary
        """
        # Prepare the combined summaries for final processing
        combined_text = "\n\n".join([
            f"Part {summary['chunk_index'] + 1}:\n{summary['summary']}"
            for summary in chunk_summaries
        ])
        
        prompt = f"""
        Below are summaries from different parts of a long meeting. Please create a final, coherent summary that:
        1. Provides an overview of the entire meeting
        2. Lists all main topics discussed in chronological order
        3. Compiles all key decisions made
        4. Lists all action items
        5. Identifies any themes or patterns across the meeting
        
        Individual summaries:
        {combined_text}
        """
        
        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=45
            )
            response.raise_for_status()
            
            return {
                "final_summary": response.json()["response"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "model_used": self.model_name,
                "number_of_chunks": len(chunk_summaries),
                "chunk_summaries": chunk_summaries
            }
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error generating final summary: {str(e)}")
            return None

    def process_long_transcript(self, transcript: str) -> Optional[Dict]:
        """
        Process a long transcript by chunking and summarizing.
        
        Args:
            transcript (str): Full transcript text
            
        Returns:
            Optional[Dict]: Final summary with metadata
        """
        # Split transcript into chunks
        chunks = self.chunk_transcript(transcript)
        
        # Generate summaries for each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            summary = self.generate_chunk_summary(chunk, i)
            if summary:
                chunk_summaries.append(summary)
            time.sleep(1)  # Rate limiting
        
        # Combine all summaries
        if chunk_summaries:
            return self.combine_summaries(chunk_summaries)
        return None

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
    
    # Define input and output paths
    input_dir = "transcripts"
    output_dir = "summaries"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process all transcript files in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, f"{filename[:-4]}_summary.json")
            
            # Read transcript
            try:
                with open(input_path, 'r', encoding='utf-8') as file:
                    transcript = file.read()
            except Exception as e:
                logging.error(f"Error reading {filename}: {str(e)}")
                continue
            
            # Process the long transcript
            summary = summarizer.process_long_transcript(transcript)
            
            # Save the summary
            if summary:
                try:
                    with open(output_path, 'w', encoding='utf-8') as file:
                        json.dump(summary, file, indent=4)
                    logging.info(f"Successfully saved summary for {filename}")
                except Exception as e:
                    logging.error(f"Error saving summary for {filename}: {str(e)}")

if __name__ == "__main__":
    main()
