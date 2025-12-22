"""
应用配置文件
"""
import os
from pathlib import Path


class Config:
    """应用配置类"""
    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 限制上传文件大小为 16MB
    
    # Debug 配置
    # 可以通过环境变量 FLASK_DEBUG=1 或 DEBUG=1 来开启
    DEBUG = os.getenv('FLASK_DEBUG', os.getenv('DEBUG', '0')).lower() in ('1', 'true', 'yes', 'on')
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'output'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    
    # 模型配置
    MODEL_PATH = os.getenv('MODEL_PATH', './best.pt')
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 创建必要的目录
        Path(Config.UPLOAD_FOLDER).mkdir(exist_ok=True)
        Path(Config.OUTPUT_FOLDER).mkdir(exist_ok=True)

