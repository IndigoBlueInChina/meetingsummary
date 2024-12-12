import os
import re
import json
from typing import Dict, List, Optional, Tuple
from langdetect import detect, DetectorFactory
from utils.llm_factory import LLMFactory
from utils.chunker import TranscriptChunker
from utils.flexible_logger import Logger

# 设置 langdetect 为确定性模式
DetectorFactory.seed = 0

class TextProofreader:
    def __init__(self):
        self.llm = LLMFactory.get_default_provider()
        self.logger = Logger(
            name="proofreader",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self.chunker = TranscriptChunker(max_tokens=2000)
        self.logger.info("TextProofreader initialized")
    
    def proofread_text(self, text: str) -> Dict[str, str]:
        """
        使用LLM模型校对输入文本
        """
        try:
            source_lang = self._detect_language(text)
            self.logger.info(f"Source text language detected: {source_lang}")
            
            chunks = self.chunker.chunk_transcript(text)
            self.logger.info(f"Text split into {len(chunks)} chunks for proofreading")
            
            proofread_chunks = []
            all_changes = []
            retry_count = 3
            
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Processing chunk {i}/{len(chunks)}")
                
                prompt = f"""Proofread the following transcript with extreme precision:

【Proofreading Guidelines】
1. Language: {source_lang}
2. Correction Scope:
   - Correct spelling errors
   - Refine colloquial expressions
   - Maintain original meaning
   - Preserve sentence structure and intent
3. DO NOT:
   - Rewrite or rephrase content
   - Add or remove substantive information
   - Change the core meaning
   - Alter technical or specific terminology

【Original Transcript】
{chunk}

Return response in JSON format:
{{
    "corrected_text": "校对后的文本",
    "corrections_made": ["修改1", "修改2", ...]
}}
"""
                for attempt in range(retry_count):
                    try:
                        # 使用 LLMProvider 的 generate 方法
                        response = self.llm.generate(
                            prompt,
                            temperature=0,  # 降低随机性
                            max_tokens=4000   # 设置最大token数
                        )
                        
                        if not response:
                            raise Exception("Empty response from LLM")
                        
                        proofread_chunk, changes = self._parse_proofreading_response(response)
                        
                        if not proofread_chunk.strip():
                            raise Exception("Empty proofread text")
                        
                        self.logger.info(f"Successfully proofread chunk {i}")
                        proofread_chunks.append(proofread_chunk)
                        all_changes.extend(changes)
                        break
                        
                    except Exception as e:
                        self.logger.warning(f"Error processing chunk {i} (attempt {attempt + 1}): {str(e)}")
                        if attempt == retry_count - 1:
                            self.logger.error(f"Failed to process chunk {i} after {retry_count} attempts")
                            proofread_chunks.append(chunk)
                            all_changes.append(f"[Error processing chunk {i}: {str(e)}]")
            
            final_proofread_text = '\n'.join(proofread_chunks)
            
            return {
                'proofread_text': final_proofread_text,
                'changes': all_changes
            }
            
        except Exception as e:
            self.logger.error(f"Proofreading failed: {str(e)}")
            raise
    
    def _detect_language(self, text: str) -> str:
        """
        检测文本语种
        
        Args:
            text: 输入文本
        Returns:
            str: 语言名称（例如：'简体中文', '繁体中文', '英文', '日文'）
        """
        try:
            lang = detect(text)
            self.logger.info(f"Detected language code: {lang}")
            
            # 对中文进行进一步判断
            if lang == 'zh':
                # 简繁体特征字符集
                simplified_chars = '简体国际办产动师见关说证'
                traditional_chars = '簡體國際辦產動師見關說證'
                
                # 计算简繁体字符出现的次数
                simplified_count = sum(text.count(char) for char in simplified_chars)
                traditional_count = sum(text.count(char) for char in traditional_chars)
                
                if traditional_count > simplified_count:
                    self.logger.info("Detected traditional Chinese characters")
                    return '繁体中文'
                else:
                    self.logger.info("Detected simplified Chinese characters")
                    return '简体中文'
            
            # 其他语言映射
            lang_mapping = {
                'en': '英文',
                'zh-cn': '简体中文',
                'zh-tw': '繁体中文',
                'ja': '日文',
                'ko': '韩文',
                'fr': '法文',
                'de': '德文',
                'es': '西班牙文',
                'it': '意大利文',
                'ru': '俄文',
                'ar': '阿拉伯文',
                'hi': '印地文',
                'pt': '葡萄牙文',
                'vi': '越南文',
                'th': '泰文'
            }
            
            detected_lang = lang_mapping.get(lang[:2], '未知语言')
            self.logger.info(f"Mapped to language name: {detected_lang}")
            return detected_lang
            
        except Exception as e:
            self.logger.warning(f"Language detection failed: {str(e)}, defaulting to English")
            return '英文'
    
    def _parse_proofreading_response(self, response: str) -> Tuple[str, List[str]]:
        """
        解析LLM返回的校对结果
        
        Args:
            response: LLM返回的JSON格式响应
        Returns:
            Tuple[str, List[str]]: (校对后的文本, 修改列表)
        """
        try:
            # 尝试解析JSON响应
            response_data = json.loads(response)
            
            # 提取校对后的文本和修改列表
            proofread_text = response_data.get('corrected_text', '')
            corrections = response_data.get('corrections_made', [])
            
            # 验证校对后的文本不为空
            if not proofread_text.strip():
                raise ValueError("Empty proofread text in response")
            
            self.logger.info(f"Successfully parsed response with {len(corrections)} corrections")
            return proofread_text, corrections
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response: {str(e)}")
            # 如果JSON解析失败，返回原始响应作为文本
            return response.strip(), ["JSON parsing failed"]
            
        except Exception as e:
            self.logger.error(f"Error parsing proofreading response: {str(e)}")
            raise