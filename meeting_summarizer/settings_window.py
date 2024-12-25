from PyQt6.QtWidgets import (QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QLineEdit, QPushButton, QComboBox, QFormLayout,
                            QMessageBox)
from PyQt6.QtCore import Qt
from config.settings import Settings
from pathlib import Path
import requests
from utils.llamaindex_llm_factory import LLMFactory
from utils.flexible_logger import Logger
import traceback

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self.logger = Logger(
            name="settings",
            console_output=True,
            file_output=True,
            log_level="INFO"
        )
        self.logger.info("Initializing settings window")
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                border-radius: 5px;
            }
            QTabBar::tab {
                padding: 8px 20px;
                margin: 2px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #4A90E2;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #4A90E2;
            }
            QComboBox {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:focus {
                border: 1px solid #4A90E2;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                background-color: #4A90E2;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton[class="secondary"] {
                background-color: white;
                border: 1px solid #E0E0E0;
                color: #333333;
            }
            QPushButton[class="secondary"]:hover {
                background-color: #F5F5F5;
            }
            QLabel {
                color: #333333;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 创建标签页
        tab_widget = QTabWidget()
        tab_widget.addTab(self.create_general_tab(), "常规")
        tab_widget.addTab(self.create_models_tab(), "模型")
        
        layout.addWidget(tab_widget)
        
        # 添加底部按钮
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        cancel_button = QPushButton("取消")
        cancel_button.setProperty("class", "secondary")  # 设置次要按钮样式
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(save_button)
        button_layout.setSpacing(10)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        save_button.clicked.connect(self.save_settings)
        cancel_button.clicked.connect(self.reject)
        
    def create_general_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 项目目录设置
        self.project_dir = QLineEdit()
        self.project_dir.setText(self.settings.get("project", "project_root"))
        browse_proj_button = QPushButton("浏览...")
        browse_proj_button.setProperty("class", "secondary")
        browse_proj_button.clicked.connect(self.browse_project_dir)
        
        proj_layout = QHBoxLayout()
        proj_layout.addWidget(self.project_dir)
        proj_layout.addWidget(browse_proj_button)
        proj_layout.setSpacing(10)
        
        layout.addRow("项目目录:", proj_layout)
        
        return tab
        
    def create_models_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # LLM提供商选择
        self.provider_combo = QComboBox()
        providers = ["ollama", "openai", "deepseek"]  # 添加 deepseek
        self.provider_combo.addItems(providers)
        current_provider = self.settings.get("llm", "provider")
        self.provider_combo.setCurrentText(current_provider)
        layout.addRow("LLM提供商:", self.provider_combo)
        
        # 模型名称
        self.model_name = QLineEdit()
        self.model_name.setText(self.settings.get("llm", "model_name"))
        layout.addRow("模型名称:", self.model_name)
        
        # API URL
        self.api_url = QLineEdit()
        self.api_url.setText(self.settings.get("llm", "api_url"))
        layout.addRow("API URL:", self.api_url)
        
        # API Key
        api_key_layout = QHBoxLayout()
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        current_provider = self.settings.get("llm", "provider")
        if current_provider == "openai":
            self.api_key.setText(self.settings.get("llm", "api_key"))
        
        toggle_visibility_button = QPushButton()
        toggle_visibility_button.setFixedSize(30, 30)
        toggle_visibility_button.setProperty("class", "icon")
        toggle_visibility_button.setStyleSheet("""
            QPushButton[class="icon"] {
                border: none;
                background-color: transparent;
                background-image: url(assets/eye-closed.png);
                background-repeat: no-repeat;
                background-position: center;
            }
            QPushButton[class="icon"][visible="true"] {
                background-image: url(assets/eye-open.png);
            }
        """)
        toggle_visibility_button.clicked.connect(self.toggle_api_key_visibility)
        
        api_key_layout.addWidget(self.api_key)
        api_key_layout.addWidget(toggle_visibility_button)
        layout.addRow("API Key:", api_key_layout)
        
        # 添加验证按钮
        verify_button = QPushButton("验证连接")
        verify_button.setProperty("class", "secondary")
        verify_button.clicked.connect(self.verify_llm_connection)
        
        # 添加状态标签
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel { padding: 5px; border-radius: 3px; }
            QLabel[status="success"] { background-color: #E8F5E9; color: #2E7D32; }
            QLabel[status="error"] { background-color: #FFEBEE; color: #C62828; }
        """)
        
        # 创建水平布局来放置验证按钮和状态标签
        verify_layout = QHBoxLayout()
        verify_layout.addWidget(verify_button)
        verify_layout.addWidget(self.status_label)
        verify_layout.addStretch()
        
        layout.addRow("", verify_layout)
        
        # 连接提供商变更信号
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        
        return tab
    
    def on_provider_changed(self, provider):
        """当LLM提供商改变时更新相关字段"""
        self.logger.info(f"Provider changed to: {provider}")
        if provider == "ollama":
            self.api_url.setText("http://localhost:11434")
            self.api_key.clear()
            self.api_key.setEnabled(False)
            self.model_name.setText("qwen2.5")  # 默认模型
        elif provider == "deepseek":
            self.api_url.setText("https://api.deepseek.com/v1")
            self.api_key.setEnabled(True)
            api_key = self.settings.get("llm", "deepseek_api_key")
            self.api_key.setText(api_key if api_key else "")
            self.model_name.setText("deepseek-chat")  # 默认模型
        else:  # openai
            self.api_url.setText("https://api.openai.com/v1")
            self.api_key.setEnabled(True)
            api_key = self.settings.get("llm", "openai_api_key")
            self.api_key.setText(api_key if api_key else "")
            self.model_name.setText("gpt-3.5-turbo")  # 默认模型
    
    def browse_project_dir(self):
        from PyQt6.QtWidgets import QFileDialog
        dir_path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if dir_path:
            self.project_dir.setText(dir_path)
    
    def save_settings(self):
        """保存设置"""
        try:
            self.logger.info("Saving settings...")
            # 保存常规设置
            self.settings.set("project", "project_root", self.project_dir.text())
            
            # 保存模型设置
            provider = self.provider_combo.currentText()
            self.settings.set("llm", "provider", provider)
            self.settings.set("llm", "model_name", self.model_name.text())
            self.settings.set("llm", "api_url", self.api_url.text())
            
            # 根据提供商保存API密钥
            if provider == "openai":
                self.settings.set("llm", "api_key", self.api_key.text())
            
            self.logger.info("Settings saved successfully")
            QMessageBox.information(self, "成功", "设置已保存")
            self.accept()
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存设置时出错：{str(e)}")
    
    def verify_llm_connection(self):
        """验证LLM连接状态"""
        try:
            provider = self.provider_combo.currentText()
            api_url = self.api_url.text().strip()
            api_key = self.api_key.text().strip()
            model_name = self.model_name.text().strip()
            
            self.logger.info(f"Verifying LLM connection - Provider: {provider}, Model: {model_name}, URL: {api_url}")
            
            if not api_url:
                self.logger.warning("API URL is empty")
                self.status_label.setText("请输入API URL")
                self.status_label.setProperty("status", "error")
                self.status_label.style().unpolish(self.status_label)
                self.status_label.style().polish(self.status_label)
                return
            
            # 更新状态标签为"检查中..."
            self.status_label.setText("检查中...")
            self.status_label.setProperty("status", "")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            
            try:
                # 创建临时配置进行测试
                factory = LLMFactory()
                
                if provider == "openai":
                    if not api_key:
                        self.logger.warning("OpenAI API key is empty")
                        self.status_label.setText("请输入API Key")
                        self.status_label.setProperty("status", "error")
                        return
                        
                    self.logger.info("Registering OpenAI provider for verification")
                    factory.register_openai(
                        api_key=api_key,
                        model=model_name,
                        api_base=api_url
                    )
                    llm = factory.get_llm("openai")
                    
                elif provider == "deepseek":
                    if not api_key:
                        self.logger.warning("DeepSeek API key is empty")
                        self.status_label.setText("请输入API Key")
                        self.status_label.setProperty("status", "error")
                        return
                        
                    self.logger.info("Registering DeepSeek provider for verification")
                    factory.register_deepseek(
                        api_key=api_key,
                        model=model_name,
                        api_base=api_url
                    )
                    llm = factory.get_llm("deepseek")
                elif provider == "ollama":
                    self.logger.info("Registering Ollama provider for verification")
                    factory.register_ollama(
                        model=model_name,
                        base_url=api_url
                    )
                    llm = factory.get_llm("ollama")
                    
                else:
                    self.logger.error(f"Unsupported provider type: {provider}")
                    self.status_label.setText(f"不支持的提供商类型: {provider}")
                    self.status_label.setProperty("status", "error")
                    return
                
                # 发送测试请求并捕获响应
                self.logger.info("Sending test request to LLM")
                try:
                    response = llm.complete("Hi")
                    self.logger.info(f"LLM response: {response}")
                    
                    # 从 CompletionResponse 对象中获取文本
                    if hasattr(response, 'text'):
                        response_text = response.text
                    else:
                        response_text = str(response)
                    
                    if response_text:
                        self.logger.info(f"LLM connection test successful, response text: {response_text}")
                        self.status_label.setText("连接成功")
                        self.status_label.setProperty("status", "success")
                    else:
                        self.logger.warning("LLM connection test failed: empty response")
                        self.status_label.setText("连接失败：空响应")
                        self.status_label.setProperty("status", "error")
                        
                except Exception as e:
                    self.logger.error(f"LLM request error: {str(e)}")
                    self.status_label.setText(f"请求错误: {str(e)}")
                    self.status_label.setProperty("status", "error")
                    
            except Exception as e:
                self.logger.error(f"LLM configuration error: {str(e)}")
                self.status_label.setText(f"配置错误: {str(e)}")
                self.status_label.setProperty("status", "error")
                
            # 刷新样式
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            
        except Exception as e:
            self.logger.error(f"Verification process error: {str(e)}")
            self.status_label.setText(f"验证出错: {str(e)}")
            self.status_label.setProperty("status", "error")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
    
    def toggle_api_key_visibility(self):
        """切换API Key的可见性"""
        button = self.sender()
        if self.api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setProperty("visible", "true")
        else:
            self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
            button.setProperty("visible", "false")
        
        # 刷新按钮样式
        button.style().unpolish(button)
        button.style().polish(button) 