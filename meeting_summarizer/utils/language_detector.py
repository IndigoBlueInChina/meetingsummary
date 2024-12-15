import re
from langdetect import detect, DetectorFactory
from utils.flexible_logger import Logger

# 设置 langdetect 为确定性模式
DetectorFactory.seed = 0

class LanguageDetector:
    def __init__(self):
        self.logger = Logger(
            name="language_detector",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        # 语言代码映射字典
        self.lang_code_mapping = {
            'zh': 'zh',      # 中文（通用）
            'zh-cn': 'zh',   # 简体中文
            'zh-tw': 'zh',   # 繁体中文
            'en': 'en',      # 英文
            'ja': 'ja',      # 日文
            'ko': 'ko',      # 韩文
            'fr': 'fr',      # 法文
            'de': 'de',      # 德文
            'es': 'es',      # 西班牙文
            'it': 'it',      # 意大利文
            'ru': 'ru',      # 俄文
            'ar': 'ar',      # 阿拉伯文
            'hi': 'hi',      # 印地文
            'pt': 'pt',      # 葡萄牙文
            'vi': 'vi',      # 越南文
            'th': 'th'       # 泰文
        }
        
        # NLTK支持的语言名称映射
        self.nltk_lang_mapping = {
            'zh': 'chinese',     # 中文
            'en': 'english',     # 英文
            'fr': 'french',      # 法文
            'de': 'german',      # 德文
            'it': 'italian',     # 意大利文
            'pt': 'portuguese',  # 葡萄牙文
            'ru': 'russian',     # 俄文
            'es': 'spanish',     # 西班牙文
            'cs': 'czech',       # 捷克文
            'da': 'danish',      # 丹麦文
            'nl': 'dutch',       # 荷兰文
            'et': 'estonian',    # 爱沙尼亚文
            'fi': 'finnish',     # 芬兰文
            'el': 'greek',       # 希腊文
            'no': 'norwegian',   # 挪威文
            'pl': 'polish',      # 波兰文
            'sl': 'slovene',     # 斯洛文尼亚文
            'sv': 'swedish',     # 瑞典文
            'tr': 'turkish'      # 土耳其文
        }

    def get_nltk_language_name(self, text: str) -> str:
        """
        检测文本语种并返回NLTK支持的语言名称
        
        Args:
            text: 输入文本
        Returns:
            str: NLTK支持的语言名称（例如：'english', 'french', 'german'等）
        """
        try:
            # 先获取标准语言代码
            lang_code = self.get_language_code(text)
            self.logger.info(f"Detected language code: {lang_code}")
            
            # 转换为NLTK支持的语言名称
            nltk_lang = self.nltk_lang_mapping.get(lang_code, 'english')
            self.logger.info(f"Mapped to NLTK language name: {nltk_lang}")
            return nltk_lang
            
        except Exception as e:
            self.logger.warning(f"NLTK language name mapping failed: {str(e)}, defaulting to 'english'")
            return 'english'

    def detect_language(self, text: str) -> str:
        """
        检测文本语种并返回友好名称
        
        Args:
            text: 输入文本
        Returns:
            str: 语言名称（例如：'简体中文', '繁体中文', '英文', '日文'）
        """
        try:
            lang = detect(text).lower()
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
                    return '繁體中文'
                else:
                    self.logger.info("Detected simplified Chinese characters")
                    return '简体中文'
            
            # 其他语言映射
            self.logger.info(f"Using mapping for language: {lang}")
            lang_mapping = {
                'en': 'English',
                'zh-cn': '简体中文',
                'zh-tw': '繁體中文',
                'ja': '日本語',
                'ko': '韓文',
                'fr': 'Français',
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
            
            detected_lang = lang_mapping.get(lang, 'unknown')
            self.logger.info(f"Mapped to language name: {detected_lang}")
            return detected_lang
            
        except Exception as e:
            self.logger.warning(f"Language detection failed: {str(e)}, defaulting to English")
            return '英文'
    
    def get_language_code(self, text: str) -> str:
        """
        检测文本语种并返回标准语言代码
        
        Args:
            text: 输入文本
        Returns:
            str: 语言代码（例如：'zh', 'en', 'ja'）
        """
        try:
            lang = detect(text).lower()
            self.logger.info(f"Detected raw language code: {lang}")
            
            # 从映射字典中获取标准化的语言代码
            standard_code = self.lang_code_mapping.get(lang, 'en')
            self.logger.info(f"Mapped to standard language code: {standard_code}")
            return standard_code
            
        except Exception as e:
            self.logger.warning(f"Language code detection failed: {str(e)}, defaulting to 'en'")
            return 'en'