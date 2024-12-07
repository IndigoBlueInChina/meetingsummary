import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

class MeetingAnalyzer:
    def __init__(self, llm_provider, chunker):
        self.llm = llm_provider
        self.chunker = chunker
        self.logger = logging.getLogger(__name__)
        
        # Load prompt templates
        prompt_dir = Path(__file__).parent / "prompt"
        self.meeting_type_template = (prompt_dir / "meetingtype.txt").read_text(encoding='utf-8')
        
        # 可以在这里加载其他特定类型会议的模板
        try:
            self.discussion_template = (prompt_dir / "discussion.txt").read_text(encoding='utf-8')
            self.class_template = (prompt_dir / "class.txt").read_text(encoding='utf-8')
        except FileNotFoundError:
            self.discussion_template = ""
            self.class_template = ""
            self.logger.warning("Optional meeting templates not found")

    def determine_meeting_type(self, text: str) -> Dict[str, Any]:
        """
        Analyze the text to determine if it's a discussion meeting or a learning session.
        """
        # Extract first chunk for meeting type analysis
        first_chunk = self.chunker.chunk_transcript(text)[0]
        
        prompt = f"""
        请根据以下评估表分析这段会议记录的类型。
        请仔细阅读会议内容，并填写评估表中的每一项。最后给出判断依据和最终结论。
        
        {self.meeting_type_template}
        
        会议内容：
        {first_chunk}
        """
        
        try:
            response = self.llm.generate(prompt)
            if not response:
                return {"type": "unknown", "analysis": "分析失败"}
            
            meeting_type = ("discussion" if "问题讨论会" in response 
                          else "lecture" if "内容分享会" in response 
                          else "unknown")
            
            return {
                "type": meeting_type,
                "analysis": response,
                "template": self._get_template_for_type(meeting_type)
            }
        except Exception as e:
            self.logger.error(f"Error determining meeting type: {str(e)}")
            return {"type": "unknown", "analysis": f"分析出错: {str(e)}", "template": ""}

    def _get_template_for_type(self, meeting_type: str) -> str:
        """
        Return the appropriate template for the meeting type.
        """
        if meeting_type == "discussion":
            return self.discussion_template
        elif meeting_type == "lecture":
            return self.class_template
        return ""

    def get_summary_prompt(self, meeting_type: str, context: str, chunk: str) -> str:
        """
        Generate an appropriate summary prompt based on meeting type.
        """
        template = self._get_template_for_type(meeting_type)
        if template:
            return f"{context}\n{template}\n\n会议内容：\n{chunk}"
        
        # 默认的提示词模板
        return f"""
        {context}
        Please analyze this section and provide:
        1. Main topics discussed in this section
        2. Key decisions made (if any)
        3. Action items mentioned (if any)
        4. Important details that should be connected with other parts
        5. Extract 5-10 key terms/phrases that best represent the content
        6. Identify the primary knowledge domains/fields this content belongs to

        Format the key terms and domains in JSON format at the end of your response like this:
        ---
        {{"key_terms": ["term1", "term2", "term3", ...], "domains": ["domain1", "domain2", ...]}}
        ---

        Here's the transcript section:
        {chunk}
        """ 

    def proofread_transcript(self, text: str, domains: List[str], key_terms: List[str]) -> str:
        """
        Proofread the transcript using domain expertise and key terms.
        """
        # Format domains and key terms for prompt
        domains_str = "、".join(domains) if domains else "通用"
        terms_str = "、".join(key_terms) if key_terms else ""
        
        prompt = f"""
        你是 {domains_str} 的专家，结合以下关键术语词汇表重新校对会议记录原文，仅订正其中的错别字，修改口语化的词句，不要对全文重新修改。
        
        关键术语词汇表：
        {terms_str}
        
        请保持原文的格式（包括换行、缩进、时间戳等），只修改必要的错误。
        如果遇到专业术语，请参考关键术语词汇表进行校对。
        
        原文：
        {text}
        """
        
        try:
            response = self.llm.generate(prompt)
            if not response:
                self.logger.error("Failed to proofread transcript")
                return text
            return response
        except Exception as e:
            self.logger.error(f"Error proofreading transcript: {str(e)}")
            return text