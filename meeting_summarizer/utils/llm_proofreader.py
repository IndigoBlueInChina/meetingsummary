import os
import re
import logging
import json
from typing import Dict, List, Optional, Tuple
from langdetect import detect, DetectorFactory

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from utils.llm_factory import LLMFactory
from utils.chunker import TranscriptChunker
from utils.flexible_logger import Logger

# 设置 langdetect 为确定性模式，确保相同文本总是返回相同的语种
DetectorFactory.seed = 0

class TextProofreader:
    """
    LLM-based text proofreading system using Ollama with Qwen model.
    
    Implements the requirements specified in the requirements document:
    - Error correction
    - Readability improvements
    - Content preservation
    - Syntax refinement
    """
    
    def __init__(self):
        self.llm = LLMFactory.get_default_provider()
        self.logger = Logger(
            name="proofreader",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self.console = Console()
        self.chunker = TranscriptChunker(max_tokens=2000)  # 使用较小的块大小用于校对
        self.logger.info("TextProofreader initialized")
    
    def _detect_language(self, text: str) -> str:
        """
        检测文本语种
        
        :param text: 输入文本
        :return: 语种代码 (例如: 'en', 'zh-cn', 'ja', etc.)
        """
        try:
            lang = detect(text)
            self.logger.info(f"Detected language: {lang}")
            return lang
        except Exception as e:
            self.logger.warning(f"Language detection failed: {str(e)}, defaulting to 'en'")
            return 'en'
    
    def proofread_text(self, text: str) -> Dict[str, str]:
        """
        Proofread the input text using LLM model.
        """
        try:
            # 只在开始时检测一次源语言
            source_lang = self._detect_language(text)
            source_lang = "简体中文"
            self.logger.info(f"Source text language detected: {source_lang}")
            
            chunks = self.chunker.chunk_transcript(text)
            self.logger.info(f"Text split into {len(chunks)} chunks for proofreading")
            
            proofread_chunks = []
            all_changes = []
            retry_count = 3
            
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Processing chunk {i}/{len(chunks)}")
                
                # Comprehensive proofreading prompt
                prompt = f"""Proofread the following transcript with extreme precision:

【Proofreading Guidelines】
1. Output Language: {source_lang}
2. Correction Scope:
   - Correct spelling errors
   - Refine colloquial expressions
   - Maintain original meaning
   - Preserve sentence structure and intent
3. DO NOT:
   - Rewrite or rephrase content
   - Add or remove substantive information
   - Change the core meaning
   - Alter technical or specific terminology

【Original Transcript】
{chunk}

Task:
- Perform careful proofreading
- Return results in strict format:
- Write a concise summary
- Return results in strict JSON format with:
  * corrected_text: Proofread transcript
  * keywords: 3-5 key terms
  * summary: Brief overview (max 150 words)
  * corrections_made: List of specific corrections

Respond with utmost precision and respect for the original text.
"""
                self.logger.info(f"Sending chunk {i} for proofreading")
                
                for attempt in range(retry_count):
                    try:
                        response = self.llm.generate(prompt)
                        if not response:
                            raise Exception("Empty response from LLM")
                        
                        proofread_chunk, changes = self._parse_proofreading_response(response)
                        
                        if not proofread_chunk.strip():
                            raise Exception("Empty proofread text")
                        
                        self.logger.info(f"Successfully proofread chunk {i}")
                        proofread_chunks.append(proofread_chunk)
                        all_changes.extend(changes)
                        break
                        
                    except Exception as e:
                        self.logger.warning(f"Error processing chunk {i} (attempt {attempt + 1}): {str(e)}")
                        if attempt == retry_count - 1:
                            self.logger.error(f"Failed to process chunk {i} after {retry_count} attempts")
                            proofread_chunks.append(chunk)
                            all_changes.append(f"[Error processing chunk {i}: {str(e)}]")
                
                self.logger.info(f"Completed chunk {i}/{len(chunks)}")
            
            final_proofread_text = '\n'.join(proofread_chunks)
            
            if all_changes:
                self.logger.info(f"Total changes made: {len(all_changes)}")
                for change in all_changes:
                    self.logger.debug(f"Change: {change}")
            
            return {
                'proofread_text': final_proofread_text,
                'changes': all_changes
            }
            
        except Exception as e:
            self.logger.error(f"Proofreading failed: {str(e)}")
            raise
    
    def _parse_proofreading_response(self, response: str) -> Tuple[str, List[str]]:
        """
        Parse the LLM's response to extract proofread text and changes.
        """
        try:
            # 确保response是字符串
            response_text = response if isinstance(response, str) else str(response)
            
            try:
                # 尝试解析JSON响应
                response_data = json.loads(response_text)
                
                # 提取所需字段
                proofread_text = response_data.get('corrected_text', '')
                keywords = response_data.get('keywords', [])
                summary = response_data.get('summary', '')
                corrections = response_data.get('corrections_made', [])
                
                if not proofread_text.strip():
                    raise ValueError("Empty proofread text in JSON response")
                
                self.logger.info(f"Successfully parsed JSON response with {len(corrections)} corrections")
                return proofread_text, corrections
                
            except json.JSONDecodeError:
                # 如果不是JSON格式，使用整个响应作为校对文本
                self.logger.warning("Response is not in JSON format, using raw text")
                return response_text.strip(), []
            
        except Exception as e:
            self.logger.error(f"Failed to parse proofreading response: {str(e)}")
            raise
    
    def display_proofreading_results(self, results: Dict[str, str]):
        """
        Display proofreading results with rich formatting.
        
        :param results: Proofreading results dictionary
        """
        # Original Text Panel
        original_panel = Panel(
            Text(results['original_text'], style="dim"),
            title="Original Text",
            border_style="blue"
        )
        
        # Proofread Text Panel
        proofread_panel = Panel(
            Text(results['proofread_text'], style="green"),
            title="Proofread Text",
            border_style="green"
        )
        
        # Display panels
        self.console.print(original_panel)
        self.console.print(proofread_panel)
        
        # Display change log
        if results['change_log']:
            self.console.print("\n[bold yellow]Changes Made:[/bold yellow]")
            for change in results['change_log']:
                self.console.print(f"- {change}")
    
    def process_file(self, input_file: str, output_file: Optional[str] = None):
        """
        Process a text file for proofreading.
        
        :param input_file: Path to the input text file
        :param output_file: Optional path to save proofread text
        """
        try:
            self.logger.info(f"Processing file: {input_file}")
            # Read input file
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            results = self.proofread_text(text)
            
            # Display results
            self.display_proofreading_results(results)
            
            # Save to output file if specified
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(results['proofread_text'])
                self.logger.info(f"Proofread text saved to {output_file}")
        
        except Exception as e:
            self.logger.error(f"File processing failed: {str(e)}")
            raise

def main():
    """
    Main function to demonstrate the proofreading system.
    """
    # Initialize proofreader
    proofreader = TextProofreader()
    
    # Example usage
    sample_text = """this is a sampl text wit sum errrors and colloqial expresions. 
its impotant to test the proofreading capabilites of our systm."""
    
    try:
        results = proofreader.proofread_text(sample_text)
        
        # Display results
        proofreader.display_proofreading_results(results)
        
        # Optionally process a file
        # proofreader.process_file('input.txt', 'output.txt')
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

# Requirements Implementation Notes:
# 1. Functional Requirements:
#    - Uses Ollama's Qwen model for intelligent proofreading
#    - Supports text input with various error types
#    - Preserves original meaning and language
#    - Provides change logging
#
# 2. Non-Functional Requirements:
#    - Logging for tracking operations
#    - Rich console output for user experience
#    - Secure file handling
#
# 3. Future Considerations:
#    - Can be extended to support multiple languages
#    - Modular design allows for easy model swapping
#    - Can be integrated with speech-to-text systems
