import os
import re
import json
from typing import Dict, List, Optional, Tuple
from utils.llm_factory import LLMFactory
from utils.chunker import TranscriptChunker
from utils.flexible_logger import Logger
from utils.language_detector import LanguageDetector

class TextProofreader:
    def __init__(self):
        self.llm = LLMFactory.get_default_provider()
        self.logger = Logger(
            name="proofreader",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self.chunker = TranscriptChunker(max_tokens=200)
        self.language_detector = LanguageDetector()
        self.logger.info("TextProofreader initialized")
    
    def proofread_text(self, text: str) -> Dict[str, str]:
        """
        使用LLM模型校对输入文本
        """
        try:
            source_lang = self.language_detector.detect_language(text)
            self.logger.info(f"Source text language detected: {source_lang}")
            
            chunks = self.chunker.chunk_transcript(text)
            self.logger.info(f"Text split into {len(chunks)} chunks for proofreading")
            
            proofread_chunks = []
            all_changes = []
            retry_count = 3
            
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Processing chunk {i}/{len(chunks)}")
                self.logger.info(f"Original chunk {i} length: {len(chunk)}")
                
                prompt = f"""
【Expert Knowledge Domain and Keyword Precise Extraction】

【Requirements】
- Language: {source_lang}
- 仅仅修改错别字，不要修改语法，不要修改句子结构，不要做任何其他的修改，直接返回修改后的文本。

【Text to Analyze】
{chunk}
"""
                # self.logger.info(f"Prompt for chunk {i}: {prompt}")
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
                        
                        self.logger.info(f"Proofread chunk {i}: {response}")
                        proofread_chunk = response
                        # proofread_chunk, changes = self._parse_proofreading_response(response)
                        
                        if not proofread_chunk.strip():
                            raise Exception("Empty proofread text")
                        
                        self.logger.info(f"Successfully proofread chunk {i}")
                        proofread_chunks.append(proofread_chunk)
                        # all_changes.extend(changes)
                        break
                        
                    except Exception as e:
                        self.logger.warning(f"Error processing chunk {i} (attempt {attempt + 1}): {str(e)}")
                        if attempt == retry_count - 1:
                            self.logger.error(f"Failed to process chunk {i} after {retry_count} attempts")
                            proofread_chunks.append(chunk)
                            # all_changes.append(f"[Error processing chunk {i}: {str(e)}]")
            
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