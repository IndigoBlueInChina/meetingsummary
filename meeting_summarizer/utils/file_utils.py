import logging
from pathlib import Path
import docx
from pymupdf4llm import LlamaMarkdownReader

def read_file_content(file_path: str) -> str:
    """
    读取不同格式的文件内容（txt, docx, pdf）
    :param file_path: 文件路径
    :return: 文件内容
    """
    file_ext = Path(file_path).suffix.lower()
    
    try:
        if file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
                
        elif file_ext == '.docx':
            doc = docx.Document(file_path)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            
        elif file_ext == '.pdf':
            md_read = LlamaMarkdownReader()
            result = md_read.load_data(file_path)
            return '\n'.join([doc.text for doc in result])
            
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
            
    except Exception as e:
        logging.error(f"读取文件 {file_path} 时出错: {str(e)}")
        raise
