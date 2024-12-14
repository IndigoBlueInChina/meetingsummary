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

    def generate_notes(self, transcript_text):
        """
        Generate structured lecture notes using LLM
        
        :param transcript_text: Lecture transcript text
        :return: Markdown formatted notes
        """
        self.logger.info("Starting notes generation")
        
        # 加载提示词模板
        prompt_template = self._load_prompt()
        if not prompt_template:
            self.logger.error("Failed to load prompt template")
            return "Error: Could not load prompt template"

        try:
            # 初始化分块器，减小块大小以加快处理速度
            chunker = TranscriptChunker(max_tokens=1500)  # 减小块大小
            chunks = chunker.chunk_transcript(transcript_text)
            self.logger.info(f"Text split into {len(chunks)} chunks for processing")

            all_notes_data = []
            retry_count = 3  # 添加重试机制
            
            # 处理每个文本块
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Processing chunk {i}/{len(chunks)}")
                
                # 填充提示词模板
                prompt = prompt_template.format(transcript_text=chunk)
                self.logger.info(f"Prompt for chunk {i}: {prompt}")

                # 添加重试逻辑
                for attempt in range(retry_count):
                    try:
                        # 使用LLM生成笔记
                        response = self.llm.generate(prompt)
                        if not response:
                            raise Exception("Empty response from LLM")

                        # 解析LLM响应
                        chunk_notes = json.loads(response)
                        all_notes_data.append(chunk_notes)
                        self.logger.info(f"Successfully processed chunk {i}")
                        break  # 成功处理，跳出重试循环
                        
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse response for chunk {i} (attempt {attempt + 1}): {str(e)}")
                        if attempt == retry_count - 1:  # 最后一次重试
                            self.logger.error(f"Failed to process chunk {i} after {retry_count} attempts")
                            # 创建一个空的笔记数据作为该块的结果
                            all_notes_data.append({
                                'keywords': [],
                                'summary': f"[Processing error in chunk {i}]",
                                'content': chunk  # 保留原始文本
                            })
                    except Exception as e:
                        self.logger.warning(f"Error processing chunk {i} (attempt {attempt + 1}): {str(e)}")
                        if attempt == retry_count - 1:
                            self.logger.error(f"Failed to process chunk {i} after {retry_count} attempts")
                            all_notes_data.append({
                                'keywords': [],
                                'summary': f"[Processing error in chunk {i}]",
                                'content': chunk
                            })

            # 检查是否有成功处理的数据
            if not all_notes_data:
                raise Exception("No valid notes generated from any chunk")

            # 合并所有块的笔记
            merged_notes = self._merge_notes_data(all_notes_data)
            self.logger.debug("Successfully merged all chunks' notes")

            # 生成最终的Markdown文档
            markdown_notes = self._format_markdown(merged_notes)
            self.logger.info("Notes generation completed successfully")
            return markdown_notes

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
