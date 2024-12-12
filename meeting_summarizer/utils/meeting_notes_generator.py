import json
from datetime import datetime
from pathlib import Path
from config.settings import Settings
from utils.flexible_logger import Logger
from utils.llm_factory import LLMFactory
from utils.chunker import TranscriptChunker

class MeetingNotesGenerator:
    def __init__(self, model='qwen'):
        """
        Initialize meeting notes generator
        
        :param model: LLM model name, default is 'qwen'
        """
        self.model = model
        self.settings = Settings()
        self.prompt_dir = Path(self.settings.config_dir) / "prompts"
        self.default_prompt_path = Path(__file__).parent / "prompts" / "meeting_notes.md"
        
        # 初始化logger
        self.logger = Logger(
            name="meeting_notes",
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
        self.user_prompt_path = self.prompt_dir / "meeting_notes.md"
        if not self.user_prompt_path.exists():
            self._copy_default_prompt()
        
        self.logger.info(f"MeetingNotesGenerator initialized with model: {model}")

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

    def generate_notes(self, transcript_text, meeting_type=None):
        """
        Generate structured meeting notes using LLM
        
        :param transcript_text: Meeting transcript text
        :param meeting_type: Optional type of meeting (e.g., 'project', 'team', 'strategy')
        :return: Markdown formatted notes
        """
        self.logger.info("Starting notes generation")
        
        # 加载提示词模板
        prompt_template = self._load_prompt()
        if not prompt_template:
            self.logger.error("Failed to load prompt template")
            return "Error: Could not load prompt template"

        try:
            # 初始化分块器
            chunker = TranscriptChunker(max_tokens=1500)
            chunks = chunker.chunk_transcript(transcript_text)
            self.logger.info(f"Text split into {len(chunks)} chunks for processing")

            all_notes_data = []
            retry_count = 3
            
            # 处理每个文本块
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Processing chunk {i}/{len(chunks)}")
                
                # 填充提示词模板
                prompt = prompt_template.format(transcript_text=chunk)
                
                for attempt in range(retry_count):
                    try:
                        response = self.llm.generate(prompt)
                        if not response:
                            raise Exception("Empty response from LLM")

                        chunk_notes = json.loads(response)
                        all_notes_data.append(chunk_notes)
                        self.logger.debug(f"Successfully processed chunk {i}")
                        break
                        
                    except Exception as e:
                        self.logger.warning(f"Error processing chunk {i} (attempt {attempt + 1}): {str(e)}")
                        if attempt == retry_count - 1:
                            self.logger.error(f"Failed to process chunk {i} after {retry_count} attempts")
                            # 创建空的笔记数据
                            all_notes_data.append({
                                'keywords': [],
                                'summary': f"[Processing error in chunk {i}]",
                                'key_discussion_points': [f"[Error processing chunk {i}]"],
                                'decisions': [],
                                'action_items': [],
                                'next_steps': []
                            })

            # 合并所有块的笔记
            merged_notes = self._merge_notes_data(all_notes_data)
            
            # 生成最终的Markdown文档
            markdown_notes = self._format_markdown(merged_notes, meeting_type)
            self.logger.info("Notes generation completed successfully")
            return markdown_notes

        except Exception as e:
            self.logger.error(f"Unexpected error during note generation: {str(e)}")
            return f"Error generating notes: {str(e)}"

    def _format_markdown(self, notes_data, meeting_type=None):
        """
        Convert notes data to Markdown format
        
        :param notes_data: Dictionary containing note information
        :param meeting_type: Optional meeting type for context
        :return: Markdown formatted notes
        """
        # Get current date and time
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Create markdown document
        markdown = f"""# Meeting Notes{f' - {meeting_type.capitalize()}' if meeting_type else ''}
*Generated: {current_datetime}*

## Keywords
{', '.join(notes_data.get('keywords', []))}

## Summary
{notes_data.get('summary', 'No summary available')}

## Key Discussion Points
{self._format_list(notes_data.get('key_discussion_points', []))}

## Decisions Made
{self._format_list(notes_data.get('decisions', []))}

## Action Items
{self._format_action_items(notes_data.get('action_items', []))}

## Next Steps
{self._format_list(notes_data.get('next_steps', []))}

---
*Notes generated automatically by AI*
"""
        return markdown

    def _format_list(self, items):
        """
        Format list items for Markdown
        
        :param items: List of items to format
        :return: Markdown formatted list
        """
        if not items:
            return "- No items recorded"
        return '\n'.join([f"- {item}" for item in items])

    def _format_action_items(self, action_items):
        """
        Format action items with owner and deadline
        
        :param action_items: List of action items
        :return: Markdown formatted action items
        """
        if not action_items:
            return "- No action items recorded"
        return '\n'.join([f"- {item.get('description', 'Unnamed action')} "
                          f"(Owner: {item.get('owner', 'Unassigned')}, "
                          f"Deadline: {item.get('deadline', 'Not specified')})"
                          for item in action_items])

    def save_notes(self, markdown_notes, filename=None):
        """
        Save Markdown notes to a file
        
        :param markdown_notes: Markdown formatted notes
        :param filename: Custom filename (optional)
        """
        if not filename:
            filename = f"meeting_notes_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_notes)
        
        print(f"Meeting notes saved to: {filename}")

# Usage example
def main():
    # Read meeting transcript
    with open('meeting_transcript.txt', 'r', encoding='utf-8') as f:
        transcript = f.read()

    # Create notes generator
    notes_generator = MeetingNotesGenerator(model='qwen')
    
    # Generate notes (optionally specify meeting type)
    markdown_notes = notes_generator.generate_notes(
        transcript, 
        meeting_type='project'
    )
    
    # Save notes
    notes_generator.save_notes(markdown_notes)

if __name__ == '__main__':
    main()
