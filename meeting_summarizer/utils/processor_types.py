from enum import Enum, auto

class ProcessorType(Enum):
    """文本处理器类型枚举"""
    PROOFREADING = "proofreading"
    LECTURE = "lecture"
    MEETING = "meeting"
    
    @classmethod
    def get_all_types(cls):
        """获取所有处理器类型"""
        return [member.value for member in cls]
    
    @classmethod
    def is_valid(cls, processor_type: str) -> bool:
        """检查处理器类型是否有效"""
        return processor_type in cls.get_all_types() 