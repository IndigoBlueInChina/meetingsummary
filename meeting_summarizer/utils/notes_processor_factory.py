from typing import Optional
from utils.llm_proofreader import TextProofreader
from utils.meeting_notes_generator import MeetingNotesGenerator
from utils.lecture_notes_generator import LectureNotesGenerator
from utils.flexible_logger import Logger
from utils.processor_types import ProcessorType

class NotesProcessorFactory:
    def __init__(self):
        self.logger = Logger(
            name="notes_processor_factory",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self._processors = {}
        
    def get_processor(self, processor_type: str):
        """
        获取或创建指定类型的处理器
        
        Args:
            processor_type: 处理器类型 (ProcessorType 枚举值)
        Returns:
            对应的处理器实例
        """
        if not ProcessorType.is_valid(processor_type):
            raise ValueError(f"Unknown processor type: {processor_type}")
            
        if processor_type not in self._processors:
            if processor_type == ProcessorType.PROOFREADING.value:
                self._processors[processor_type] = TextProofreader()
            elif processor_type == ProcessorType.LECTURE.value:
                self._processors[processor_type] = LectureNotesGenerator()
            elif processor_type == ProcessorType.MEETING.value:
                self._processors[processor_type] = MeetingNotesGenerator()
            
            self.logger.info(f"Created new processor of type: {processor_type}")
            
        return self._processors[processor_type]
    
    def process_text(self, text: str, processor_type: str, progress_callback=None, topic: str = "", keywords: str = "") -> dict:
        """
        处理文本
        
        Args:
            text: 要处理的文本
            processor_type: 处理器类型
            progress_callback: 进度回调函数
            topic: 主题内容
            keywords: 关键字内容(多个关键字可用空格分隔)
        Returns:
            处理结果
        """
        try:
            self.logger.info(f"开始使用 {processor_type} 处理器处理文本")
            processor = self.get_processor(processor_type)
            
            # 格式化关键字 - 将空格分隔的关键字转换为逗号分隔
            formatted_keywords = ",".join(
                [kw.strip() for kw in keywords.split() if kw.strip()]
            )
            self.logger.info(f"格式化后的关键字: {formatted_keywords}")
            
            # 为处理器设置主题和格式化后的关键字
            if hasattr(processor, 'set_context'):
                processor.set_context(topic=topic, keywords=formatted_keywords)
                self.logger.info(f"已设置处理器上下文 - 主题: {topic}, 关键字: {formatted_keywords}")
            
            if processor_type == ProcessorType.PROOFREADING.value:
                result = processor.proofread_text(text, progress_callback)
                self.logger.info("基础校对处理完成")
                return result
            else:
                self.logger.info(f"使用 {processor_type} 处理器生成笔记")
                return {
                    'markdown_notes': processor.generate_notes(text),
                    'changes': []
                }
                
        except Exception as e:
            self.logger.error(f"使用 {processor_type} 处理器处理文本失败: {str(e)}")
            raise
