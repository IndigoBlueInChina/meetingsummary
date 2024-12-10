import logging
import os
from typing import Optional, Dict, List, Any
import json
import re
from pathlib import Path
from .chunker import TranscriptChunker
from meeting_summarizer.utils.llm_factory import LLMFactory
from meeting_summarizer.config.settings import Settings

class MeetingSummarizer:
    def __init__(self, 
                 provider_type: str = "ollama",
                 provider_config: Dict[str, Any] = None):
        settings = Settings()  # 获取设置实例
        if provider_config is None:
            provider_config = settings._settings["llm"]  # 使用 LLM 配置
        
        self.llm = LLMFactory.create_provider(provider_type, **provider_config)
        self.chunker = TranscriptChunker(max_tokens=4000)
        self.logger = logging.getLogger(__name__)
        
        # 加载提示模板
        prompt_dir = Path(__file__).parent / "prompt"
        try:
            self.summary_template = (prompt_dir / "summary.txt").read_text(encoding='utf-8')
        except FileNotFoundError:
            self.summary_template = """
            请根据以下会议内容生成一个详细的总结。总结应包含：
            1. 会议主要议题
            2. 关键讨论点
            3. 重要决策
            4. 后续行动项

            会议内容：
            {text}
            """
            self.logger.warning("Summary template not found, using default")

    def generate_chunk_summary(self, chunk: str, chunk_index: int, total_chunks: int) -> Optional[Dict]:
        """生成单个文本块的总结"""
        try:
            context = f"这是会议记录的第 {chunk_index + 1} 部分，共 {total_chunks} 部分。"
            
            # 提取时间上下文（如果有）
            first_timestamp_match = re.search(r'\[\d{2}:\d{2}:\d{2}\]|\d{2}:\d{2}:\d{2}|\(\d{2}:\d{2}\)', chunk)
            last_timestamp_match = re.search(r'\[\d{2}:\d{2}:\d{2}\]|\d{2}:\d{2}:\d{2}|\(\d{2}:\d{2}\)', chunk[::-1])
            
            if first_timestamp_match and last_timestamp_match:
                context += f"\n此部分时间范围：{first_timestamp_match.group()} 到 {last_timestamp_match.group()}"
            
            prompt = self.summary_template.format(
                context=context,
                text=chunk
            )
            
            response = self.llm.generate(prompt)
            if not response:
                return None
                
            return {
                "summary": response,
                "start_time": first_timestamp_match.group() if first_timestamp_match else None,
                "end_time": last_timestamp_match.group() if last_timestamp_match else None
            }
            
        except Exception as e:
            self.logger.error(f"生成块总结时出错: {str(e)}")
            return None

    def generate_summary(self, text: str, output_file: str = None) -> Optional[str]:
        """
        生成会议总结
        :param text: 输入文本
        :param output_file: 输出文件路径（可选）
        :return: 生成的总结文本
        """
        try:
            self.logger.info("开始生成会议总结...")
            
            # 分块处理文本
            chunks = self.chunker.chunk_transcript(text)
            if not chunks:
                self.logger.error("文本分块失败")
                return None
                
            # 处理每个块并收集总结
            summaries = []
            for i, chunk in enumerate(chunks):
                chunk_summary = self.generate_chunk_summary(chunk, i, len(chunks))
                if chunk_summary:
                    summaries.append(chunk_summary)
            
            if not summaries:
                self.logger.error("没有生成任何有效的总结")
                return None
            
            # 合并所有总结
            combined_summary = self._merge_summaries(summaries)
            
            # 如果提供了输出文件路径，保存总结
            if output_file:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(combined_summary)
                self.logger.info(f"总结已保存到: {output_file}")
            
            return combined_summary
            
        except Exception as e:
            self.logger.error(f"生成总结时出错: {str(e)}")
            return None

    def _merge_summaries(self, summaries: List[Dict]) -> str:
        """合并多个块的总结"""
        try:
            # 提取所有总结文本
            summary_texts = [s["summary"] for s in summaries if s and s.get("summary")]
            
            if not summary_texts:
                return ""
            
            # 如果只有一个总结，直接返回
            if len(summary_texts) == 1:
                return summary_texts[0]
            
            # 合并多个总结
            merged_text = "\n\n".join(summary_texts)
            
            # 生成最终总结
            prompt = f"""
            请将以下多个会议片段的总结合并为一个连贯的总结：

            {merged_text}
            """
            
            final_summary = self.llm.generate(prompt)
            return final_summary if final_summary else merged_text
            
        except Exception as e:
            self.logger.error(f"合并总结时出错: {str(e)}")
            return "\n\n".join(summary_texts) if summary_texts else ""

# 全局变量用于缓存总结器实例
_summarizer = None

def get_summarizer(provider_type: str = "ollama", provider_config: Dict[str, Any] = None) -> MeetingSummarizer:
    """获取或创建总结器实例"""
    global _summarizer
    if _summarizer is None:
        _summarizer = MeetingSummarizer(provider_type, provider_config)
    return _summarizer

def generate_summary(text: str, output_file: str = None) -> Optional[str]:
    """
    生成会议总结的包装函数
    :param text: 输入文本
    :param output_file: 输出文件路径（可选）
    :return: 生成的总结文本
    """
    summarizer = get_summarizer()
    return summarizer.generate_summary(text, output_file)