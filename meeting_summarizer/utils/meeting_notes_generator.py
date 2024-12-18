import re
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
        
        # 初始化主题和关键字属性
        self._topic = ""
        self._keywords = ""
        self._stop_flag = False  # 添加停止标志
        self.logger.info("MeetingNotesGenerator initialized")

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

    def stop(self):
        """设置停止标志"""
        self._stop_flag = True
        self.logger.info("Stop flag set")
        
    def reset(self):
        """重置停止标志"""
        self._stop_flag = False
        self.logger.info("Stop flag reset")

    def generate_notes(self, transcript_text, meeting_type=None):
        """
        Generate structured meeting notes using LLM
        
        :param transcript_text: Meeting transcript text
        :param meeting_type: Optional type of meeting (e.g., 'project', 'team', 'strategy')
        :return: Markdown formatted notes
        """
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
                        self.logger.info(f"Original response: {response}")
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
                                'key_discussion_points': [f"[Error processing chunk {i}]"],
                                'decisions': [],
                                'action_items': [],
                                'next_steps': []
                            })

            # Update progress for merging notes
            if hasattr(self, 'progress_callback'):
                self.progress_callback(90, "Merging processed results...")

            # Merge all notes data
            merged_notes = self._merge_notes_data(all_notes_data)
            
            # Generate final Markdown document
            if hasattr(self, 'progress_callback'):
                self.progress_callback(95, "Generating final document...")
            
            markdown_notes = self._format_markdown(merged_notes, meeting_type)
            
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

    def _clean_response(self, response):
        """清理 LLM 响应中的额外标记和非法字符"""
        try:
            # 使用正则表达式提取 Markdown 代码块中的 JSON 内容
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)  # 提取 JSON 内容
            else:
                self.logger.warning("No JSON found in the response")

            # 移除可能的 Markdown 代码块标记
            response = re.sub(r'^```\w*\n', '', response)
            response = re.sub(r'\n```$', '', response)
            
            # 移除或替换非法的控制字符
            response = re.sub(r'[\x00-\x1F\x7F]', '', response)
            
            # 移除其他可能的干扰字符
            response = response.strip()
            
            # 尝试验证是否为有效的 JSON
            json.loads(response)  # 如果无效会抛出异常
            
            return response
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON after cleaning: {str(e)}")
            # 进一步清理尝试
            try:
                # 使用更严格的清理
                response = re.sub(r'[^\x20-\x7E\n]', '', response)
                # 验证清理后的结果
                json.loads(response)
                return response
            except:
                raise ValueError("Unable to clean response into valid JSON")

    def set_progress_callback(self, callback):
        """设置进度更新回调函数"""
        self.progress_callback = callback

    def _merge_notes_data(self, all_notes_data):
        """合并所有块的笔记数据"""
        merged_data = {
            'keywords': [],
            'summary': '',
            'key_discussion_points': [],
            'decisions': [],
            'action_items': [],
            'next_steps': []
        }
        
        for notes in all_notes_data:
            merged_data['keywords'].extend(notes.get('keywords', []))
            merged_data['summary'] += notes.get('summary', '') + ' '
            merged_data['key_discussion_points'].extend(notes.get('key_discussion_points', []))
            merged_data['decisions'].extend(notes.get('decisions', []))
            merged_data['action_items'].extend(notes.get('action_items', []))
            merged_data['next_steps'].extend(notes.get('next_steps', []))
        
        # Optionally, you can clean up or summarize the merged data here
        merged_data['keywords'] = list(set(merged_data['keywords']))  # Remove duplicates
        merged_data['summary'] = merged_data['summary'].strip()  # Clean up summary
        
        return merged_data

    def optimize_notes(self, markdown_notes):
        """
        Submit the generated notes to the LLM for optimization and coherence.
        
        :param markdown_notes: Markdown formatted notes to be optimized
        :return: Optimized Markdown formatted notes
        """
        self.logger.info("Starting notes optimization")
        
        prompt = f"Please based on the topic {self._topic} and keywords {self._keywords} to optimize the following meeting notes for coherence and clarity:\n\n{markdown_notes}"
        
        try:
            optimized_response = self.llm.generate(prompt)
            self.logger.info("Notes optimization completed successfully")
            return optimized_response
        except Exception as e:
            self.logger.error(f"Error during notes optimization: {str(e)}")
            return markdown_notes  # Return original notes in case of error

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
