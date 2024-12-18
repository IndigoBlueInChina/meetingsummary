import re
import json
from datetime import datetime
from pathlib import Path
from config.settings import Settings
from utils.flexible_logger import Logger
from utils.llm_factory import LLMFactory
from utils.chunker import TranscriptChunker

class LectureNotesGenerator:
    def __init__(self, model=''):
        """
        Initialize lecture notes generator
        
        :param model: LLM model name, default is ''
        """
        self.model = model
        self.settings = Settings()
        self.prompt_dir = Path(self.settings.config_dir) / "prompts"
        self.default_prompt_path = Path(__file__).parent / "prompts" / "lecture_notes.md"
        
        # 初始化logger
        self.logger = Logger(
            name="lecture_notes",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        
        # 初始化LLM
        self.llm = LLMFactory.get_default_provider()
        self.logger.debug(f"Initialized LLM provider: {type(self.llm).__name__}")
        
        # 确保提示词目录存在
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Prompt directory: {self.prompt_dir}")
        
        # 如果用户配置目录下没有提示词文件，复制默认文件
        self.user_prompt_path = self.prompt_dir / "lecture_notes.md"
        if not self.user_prompt_path.exists():
            self._copy_default_prompt()
        
        self.logger.info(f"LectureNotesGenerator initialized with model: {model}")
        
        # 初始化主题和关键字属性
        self._topic = ""
        self._keywords = ""
        self._stop_flag = False  # 添加停止标志
        self.logger.info("LectureNotesGenerator initialized")

    def _copy_default_prompt(self):
        """复制默认提示词文件到用户配置目录"""
        try:
            if self.default_prompt_path.exists():
                with open(self.default_prompt_path, 'r', encoding='utf-8') as src:
                    prompt_content = src.read()
                with open(self.user_prompt_path, 'w', encoding='utf-8') as dst:
                    dst.write(prompt_content)
                self.logger.info("Default prompt template copied to user config directory")
            else:
                self.logger.error("Default prompt template not found")
        except Exception as e:
            self.logger.error(f"Failed to copy default prompt file: {str(e)}")

    def _load_prompt(self):
        """加载提示词模板"""
        self.logger.debug(f"Loading user_prompt_path: {self.user_prompt_path}")
        self.logger.debug(f"Loading default_prompt_path: {self.default_prompt_path}")   
        try:
            # 优先使用用户配置的提示词
            if self.user_prompt_path.exists():
                self.logger.debug("Loading user prompt template")
                with open(self.user_prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            # 如果用户配置不存在，使用默认提示词
            elif self.default_prompt_path.exists():
                self.logger.debug("Loading default prompt template")
                with open(self.default_prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.error("No prompt template found")
                raise FileNotFoundError("No prompt template found")
        except Exception as e:
            self.logger.error(f"Error loading prompt template: {str(e)}")
            return None

    def stop(self):
        """设置停止标志"""
        self._stop_flag = True
        self.logger.info("Stop flag set")
        
    def reset(self):
        """重置停止标志"""
        self._stop_flag = False
        self.logger.info("Stop flag reset")

    def _clean_response(self, response):
        """清理 LLM 响应中的额外标记和非法字符"""
        try:
            # 移除日志前缀
            self.logger.debug(f"移除日志前缀 response: {response}")
            response = re.sub(r'(\[.*?\] \[INFO\] LLM response: )+', '', response)
            
            # 移除非法字符
            self.logger.debug(f"移除非法字符 response: {response}")
            response = re.sub(r'[\x00-\x1F\x7F]', '', response)
            response = response.strip()
            
            self.logger.debug(f"Cleaned response: {response}")

            # 首先尝试从代码块中提取
            code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', response, re.DOTALL)
            if code_block_match:
                response = code_block_match.group(1).strip()

            # 然后尝试提取最外层的 JSON 对象
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON object found in response")

            json_str = json_match.group(1).strip()
            
            # 验证 JSON 格式并检查必需的键
            parsed_json = json.loads(json_str)
            if not all(key in parsed_json for key in ['keywords', 'summary', 'content']):
                raise ValueError("Missing required keys in JSON")

            return json_str

        except Exception as e:
            self.logger.error(f"Error cleaning response: {str(e)}")
            self.logger.debug(f"Original response: {response}")
            raise ValueError(f"Unable to clean response into valid JSON: {str(e)}")

    def optimize_notes(self, markdown_notes):
        """
        Submit the generated notes to the LLM for optimization and coherence.
        
        :param markdown_notes: Markdown formatted notes to be optimized
        :return: Optimized Markdown formatted notes
        """
        self.logger.info("Starting notes optimization")
        
        prompt = f"Please based on the topic {self._topic} and keywords {self._keywords} to optimize the following lecture notes for coherence and clarity:\n\n{markdown_notes}"
        
        try:
            optimized_response = self.llm.generate(prompt)
            self.logger.info("Notes optimization completed successfully")
            return optimized_response
        except Exception as e:
            self.logger.error(f"Error during notes optimization: {str(e)}")
            return markdown_notes  # Return original notes in case of error

    def generate_notes(self, transcript_text):
        """
        Generate structured lecture notes using LLM
        
        :param transcript_text: Lecture transcript text
        :return: Markdown formatted notes
        """
        try:
            self.reset()  # Reset stop flag
            self.logger.info("Starting notes generation")
            
            # Load prompt template
            prompt_template = self._load_prompt()
            if not prompt_template:
                self.logger.error("Failed to load prompt template")
                return "Error: Could not load prompt template"

            try:
                # Initialize chunker
                chunker = TranscriptChunker(max_tokens=2000)
                chunks = chunker.chunk_transcript(transcript_text)
                total_chunks = len(chunks)
                self.logger.info(f"Text split into {total_chunks} chunks for processing")

                all_notes_data = []
                retry_count = 3
                
                # Process each text chunk
                for i, chunk in enumerate(chunks, 1):
                    # Calculate current progress percentage
                    progress = int((i - 1) * 90 / total_chunks)  # Reserve 10% for final merge
                    
                    # Check if stop flag is set
                    if self._stop_flag:
                        self.logger.info("Notes generation stopped by user")
                        raise Exception("Operation cancelled by user")

                    self.logger.info(f"Processing chunk {i}/{total_chunks}")
                    # Send progress update
                    if hasattr(self, 'progress_callback'):
                        self.progress_callback(progress, f"Processing chunk {i}/{total_chunks}...")

                    # Fill in the prompt template
                    prompt_parts = []
                    if getattr(self, '_topic', '').strip():
                        prompt_parts.append(f"【Topic】\n{self._topic}")
                    if getattr(self, '_keywords', '').strip():
                        prompt_parts.append(f"【Keywords】\n{self._keywords}")
                    prompt_parts.append(prompt_template)
                    prompt_parts.append(f"【Text】\n{chunk}")
                    prompt = "\n".join(prompt_parts)
                    
                    for attempt in range(retry_count):
                        # Check if stop flag is set again
                        if self._stop_flag:
                            self.logger.info("Notes generation stopped by user")
                            raise Exception("Operation cancelled by user")

                        try:
                            response = self.llm.generate(prompt)
                            self.logger.info(f"LLM response: {response}")
                            if not response:
                                raise Exception("Empty response from LLM")

                            # Clean response
                            cleaned_response = self._clean_response(response)
                            chunk_notes = json.loads(cleaned_response)
                            all_notes_data.append(chunk_notes)
                            self.logger.info(f"Successfully processed chunk {i}")
                            break  # Successfully processed, exit retry loop
                            
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"Failed to parse response for chunk {i} (attempt {attempt + 1}): {str(e)}")
                            if attempt == retry_count - 1:  # Last retry
                                self.logger.error(f"Failed to process chunk {i} after {retry_count} attempts")
                                all_notes_data.append({
                                    'keywords': [],
                                    'summary': f"[Processing error in chunk {i}]",
                                    'content': chunk  # Keep original text
                                })

                # Update progress for merging notes
                if hasattr(self, 'progress_callback'):
                    self.progress_callback(90, "Merging processed results...")

                # Merge all notes data
                merged_notes = self._merge_notes_data(all_notes_data)
                
                # Generate final Markdown document
                if hasattr(self, 'progress_callback'):
                    self.progress_callback(95, "Generating final document...")
                
                markdown_notes = self._format_markdown(merged_notes)
                
                # Optimize the generated notes
                markdown_notes = self.optimize_notes(markdown_notes)
                
                # Final progress update
                if hasattr(self, 'progress_callback'):
                    self.progress_callback(100, "Processing complete")
                
                self.logger.info("Notes generation completed successfully")
                return markdown_notes

            except Exception as e:
                self.logger.error(f"Unexpected error during note generation: {str(e)}")
                return f"Error generating notes: {str(e)}"

        except Exception as e:
            self.logger.error(f"Unexpected error during note generation: {str(e)}")
            return f"Error generating notes: {str(e)}"

    def _merge_notes_data(self, all_notes_data):
        """
        Merge notes data from multiple chunks
        
        :param all_notes_data: List of note data dictionaries from each chunk
        :return: Merged notes data dictionary
        """
        self.logger.debug("Merging notes data from all chunks")
        
        # 合并所有关键词（去重）
        all_keywords = set()
        for notes in all_notes_data:
            all_keywords.update(notes.get('keywords', []))
        
        # 合并摘要（取第一个块的摘要作为主摘要）
        main_summary = all_notes_data[0].get('summary', 'No summary available')
        
        # 合并详细内容
        merged_content = []
        for notes in all_notes_data:
            content = notes.get('content', '').strip()
            if content:
                merged_content.append(content)
        
        return {
            'keywords': list(all_keywords),
            'summary': main_summary,
            'content': '\n\n'.join(merged_content)
        }

    def _format_markdown(self, notes_data):
        """
        Convert notes data to Markdown format
        
        :param notes_data: Dictionary containing note information
        :return: Markdown formatted notes
        """
        self.logger.debug("Formatting markdown with notes data")
        
        # Get current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        markdown = f"""# Lecture Notes ({current_date})

## Keywords
{', '.join(notes_data.get('keywords', []))}

## Summary
{notes_data.get('summary', 'No summary available')}

## Detailed Content
{notes_data.get('content', 'No detailed content available')}

---
*Notes generated automatically by AI*
"""
        return markdown

    def save_notes(self, markdown_notes, filename=None):
        """
        Save Markdown notes to a file
        
        :param markdown_notes: Markdown formatted notes
        :param filename: Filename, defaults to current date
        """
        if not filename:
            filename = f"lecture_notes_{datetime.now().strftime('%Y%m%d')}.md"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(markdown_notes)
            self.logger.info(f"Notes saved successfully to: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save notes to {filename}: {str(e)}")
            raise

    @property
    def topic(self):
        """获取主题"""
        return self._topic if hasattr(self, '_topic') else ""

    @property
    def keywords(self):
        """获取关键字"""
        return self._keywords if hasattr(self, '_keywords') else ""

    def set_context(self, topic: str = "", keywords: str = ""):
        """设置处理上下文"""
        try:
            self._topic = topic.strip()
            self._keywords = keywords.strip()
            self.logger.info(f"Context set - Topic: {self._topic}, Keywords: {self._keywords}")
        except Exception as e:
            self.logger.error(f"Error setting context: {str(e)}")
            self._topic = ""
            self._keywords = ""

# Usage example
def main():
    # Read transcript
    with open('lecture_transcript.txt', 'r', encoding='utf-8') as f:
        transcript = f.read()

    # Create notes generator
    notes_generator = LectureNotesGenerator(model='')
    
    # Generate notes
    markdown_notes = notes_generator.generate_notes(transcript)
    
    # Save notes
    notes_generator.save_notes(markdown_notes)

if __name__ == '__main__':
    main()
