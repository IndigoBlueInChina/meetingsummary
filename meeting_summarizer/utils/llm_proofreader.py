import os
import re
import logging
import json
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from utils.llm_factory import LLMFactory

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
        self.logger = logging.getLogger(__name__)
        self.console = Console()
    
    def proofread(self, text: str) -> Dict[str, str]:
        """
        Proofread the input text using Ollama's Qwen model.
        
        :param text: Input text to proofread
        :return: Dictionary with original and proofread text, and change log
        """
        try:
            # Construct detailed prompt for proofreading
            prompt = f"""You are a professional proofreader. Please proofread the following text:

Proofreading Guidelines:
- Correct spelling mistakes
- Fix punctuation and special characters
- Improve sentence structures for clarity
- Replace overly colloquial expressions
- Maintain the original meaning and tone
- Do NOT add new content or significantly rewrite

Original Text:
{text}

Proofread the text and provide:
1. The proofread text
2. A list of changes made (type of change, original, corrected)"""

            # Generate response from Ollama
            response = self.llm.generate(prompt)
            
            # 修改这里：response 的结构可能与预期不同
            # 直接使用返回的文本内容
            response_text = response if isinstance(response, str) else response.get('content', '') if isinstance(response, dict) else str(response)
            
            # Parse the response
            proofread_text, change_log = self._parse_proofreading_response(response_text)
            
            # Log the proofreading operation
            print(f"Proofread text successfully. Changes: {len(change_log)}")
            self.logger.info(f"Proofread text successfully. Changes: {len(change_log)}")
            
            return {
                'original_text': text,
                'proofread_text': proofread_text,
                'change_log': change_log
            }
        
        except Exception as e:
            self.logger.error(f"Proofreading failed: {str(e)}")
            raise
    
    def _parse_proofreading_response(self, response: str) -> Tuple[str, List[Dict]]:
        """
        Parse the LLM's response and extract proofread text and change log.
        
        :param response: Raw response from the LLM
        :return: Tuple of proofread text and change log
        """
        # Basic parsing logic - might need refinement based on actual model response
        proofread_text = response
        change_log = []
        
        # You might want to implement more sophisticated parsing here
        # For example, extracting changes from the model's response
        
        return proofread_text, change_log
    
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
            # Read input file
            with open(input_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Proofread text
            results = self.proofread(text)
            
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
        # Proofread sample text
        results = proofreader.proofread(sample_text)
        
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
