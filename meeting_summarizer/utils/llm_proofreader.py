import os
import re
import json
from typing import Dict, List, Optional, Tuple
from utils.llamaindex_llm_factory import LLMFactory
from utils.chunker import TranscriptChunker
from utils.flexible_logger import Logger
from utils.language_detector import LanguageDetector

class TextProofreader:
    def __init__(self):
        self.logger = Logger(
            name="proofreader",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        
        try:
            # 直接获取 LLM 实例，注意这里使用 self.llm 而不是 self._llm
            self.llm = LLMFactory.get_llm_instance()
            self.logger.info("LLM initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {str(e)}")
            raise
            
        self.chunker = TranscriptChunker(max_tokens=2000)
        self.language_detector = LanguageDetector()
        self._stop_flag = False
        self._topic = ""
        self._keywords = ""
        self.logger.info("TextProofreader initialized")
    
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
    
    def stop(self):
        """设置停止标志"""
        self._stop_flag = True
        
    def reset(self):
        """重置停止标志"""
        self._stop_flag = False
    
    def expand_keywords(self) -> List[str]:
        """
        Expand the keyword set based on the topic and existing keywords.
        
        :return: Expanded list of keywords
        """
        expanded_keywords = set(self._keywords.split(", "))  # Start with existing keywords
        if self._topic:
            # Here you can implement logic to generate additional keywords based on the topic
            # For example, you could use the LLM to generate related keywords
            prompt = f"Generate more keywords with comma-separated list and related to the topic: {self._topic} and the keywords: {self._keywords}"
            try:
                # 使用新的 LLM 接口
                response = self.llm.complete(prompt)
                if response:
                    additional_keywords = response.split(", ")
                    expanded_keywords.update(additional_keywords)
                    self.logger.info(f"Keywords expanded: {len(additional_keywords)} new keywords added")
            except Exception as e:
                self.logger.error(f"Error generating additional keywords: {str(e)}")
        
        return list(expanded_keywords)

    def proofread_text(self, text: str, progress_callback=None) -> Dict[str, str]:
        """
        使用LLM模型校对输入文本
        
        Args:
            text: 要校对的文本
            progress_callback: 进度回调函数，接收两个参数：进度百分比(int)和状态文本(str)
        """
        try:
            self.reset()  # 重置停止标志
            source_lang = self.language_detector.detect_language(text)
            self.logger.info(f"Source text language detected: {source_lang}")
            
            # Expand keywords before proofreading
            expanded_keywords = self.expand_keywords()
            self.logger.info(f"Expanded keywords: {expanded_keywords}")
            
            chunks = self.chunker.chunk_transcript(text)
            total_chunks = len(chunks)
            self.logger.info(f"Text split into {total_chunks} chunks for proofreading")
            
            proofread_chunks = []
            all_changes = []
            retry_count = 3
            
            for i, chunk in enumerate(chunks, 1):
                # 检查是否需要停止
                if self._stop_flag:
                    self.logger.info("Proofreading stopped by user")
                    raise Exception("操作已被用户取消")
                
                # 更新进度
                if progress_callback:
                    progress = int((i - 1) / total_chunks * 100)
                    progress_callback(progress, f"正在处理第 {i}/{total_chunks} 段")
                
                self.logger.info(f"Processing chunk {i}/{total_chunks}")
                self.logger.info(f"Original chunk {i} length: {len(chunk)}")
                
                # 增加一个处理，将chunk中的换行符替换为空格，使其为一段话。
                chunk = chunk.replace('\n', ' ')
                
                # 修改提示模板，使其更加明确
                prompt_parts = [
                    "【Task】",
                    "校对以下文本，仅修改错别字和标点符号。保持原文的完整性，不要删减或增加内容。",
                    "",
                    "【Requirements】",
                    "1. 必须返回完整的文本",
                    "2. 仅修改错别字和标点符号",
                    "3. 不要修改语法",
                    "4. 不要修改句子结构",
                    "5. 不要做任何其他修改",
                    f"6. 语言: {source_lang}",
                    ""
                ]
                
                if self._topic:
                    prompt_parts.extend([
                        "【Topic】",
                        self._topic,
                        ""
                    ])
                
                if self._keywords:
                    prompt_parts.extend([
                        "【Keywords】",
                        self._keywords,
                        ""
                    ])
                
                prompt_parts.extend([
                    "【Text to Proofread】",
                    chunk,
                    "",
                    "【Instructions】",
                    "直接返回校对后的完整文本，不要添加任何额外的标记或说明。"
                ])
                
                prompt = "\n".join(prompt_parts)
                
                for attempt in range(retry_count):
                    # 再次检查是否需要停止
                    if self._stop_flag:
                        self.logger.info("Proofreading stopped by user")
                        raise Exception("操作已被用户取消")
                        
                    try:
                        # 使用 LlamaIndex LLM 接口
                        self.logger.info(f"Prompt for chunk {i}: {prompt}")
                        response = self.llm.complete(prompt)
                        # 从 CompletionResponse 对象中获取文本内容
                        proofread_chunk = response.text
                        
                        if not proofread_chunk or not proofread_chunk.strip():
                            raise Exception("Empty response from LLM")
                        
                        self.logger.info(f"LLM response for chunk {i}: {proofread_chunk}")
                        self.logger.info(f"Successfully proofread chunk {i}")
                        proofread_chunks.append(proofread_chunk)
                        break
                        
                    except Exception as e:
                        self.logger.warning(f"Error processing chunk {i} (attempt {attempt + 1}): {str(e)}")
                        if attempt == retry_count - 1:
                            self.logger.error(f"Failed to process chunk {i} after {retry_count} attempts")
                            proofread_chunks.append(chunk)
            
            # 完成处理
            if progress_callback:
                progress_callback(100, "校对完成")
            
            final_proofread_text = '\n'.join(proofread_chunks)
            
            return {
                'proofread_text': final_proofread_text,
                'changes': all_changes
            }
            
        except Exception as e:
            self.logger.error(f"Proofreading failed: {str(e)}")
            raise
    
    def _parse_proofreading_response(self, response: str) -> Tuple[str, List[str]]:
        """
        解析LLM返回的校对结果
        
        Args:
            response: LLM返回的JSON格式响应
        Returns:
            Tuple[str, List[str]]: (校对后的文本, 修改列表)
        """
        self.logger.info(f"Trying to parse response: {response}")
        return response.strip(),[]
        try:
            # 尝试解析JSON响应
            self.logger.info(f"Trying to parse response: {response}")
            
            response_data = json.loads(response)
            self.logger.info("JSON response: {response_data}")

            # 提取校对后的文本和修改列表
            proofread_text = response_data.get('corrected_text', '')
            self.logger.info(f"Proofread text: {proofread_text}")

            corrections = response_data.get('corrections_made', [])
            self.logger.info(f"Corrections: {corrections}")

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