from typing import Optional
from utils.llm_proofreader import TextProofreader
from utils.meeting_notes_generator import MeetingNotesGenerator
from utils.lecture_notes_generator import LectureNotesGenerator
from utils.flexible_logger import Logger

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
            processor_type: 处理器类型 ('basic', 'lecture', 'meeting')
        Returns:
            对应的处理器实例
        """
        if processor_type not in self._processors:
            if processor_type == "basic":
                self._processors[processor_type] = TextProofreader()
            elif processor_type == "lecture":
                self._processors[processor_type] = LectureNotesGenerator()
            elif processor_type == "meeting":
                self._processors[processor_type] = MeetingNotesGenerator()
            else:
                raise ValueError(f"Unknown processor type: {processor_type}")
            
            self.logger.info(f"Created new processor of type: {processor_type}")
            
        return self._processors[processor_type]
    
    def process_text(self, text: str, processor_type: str, progress_callback=None) -> dict:
        """
        处理文本
        
        Args:
            text: 要处理的文本
            processor_type: 处理器类型
            progress_callback: 进度回调函数
        Returns:
            处理结果
        """
        try:
            self.logger.info(f"开始使用 {processor_type} 处理器处理文本")
            processor = self.get_processor(processor_type)
            
            if processor_type == "basic":
                result = processor.proofread_text(text, progress_callback)
                self.logger.info("基础校对处理完成")
                return result
            else:
                self.logger.info(f"使用 {processor_type} 处理器生成笔记")
                return {
                    'proofread_text': processor.generate_notes(text),
                    'changes': []
                }
                
        except Exception as e:
            self.logger.error(f"使用 {processor_type} 处理器处理文本失败: {str(e)}")
            raise
