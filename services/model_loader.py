"""
模型加载器 - 管理 YOLO 和 OCR 模型的初始化
"""
import os
from ultralytics import YOLO
from paddleocr import PaddleOCR


class ModelLoader:
    """模型加载器单例类"""
    _instance = None
    _yolo_model = None
    _ocr_model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._yolo_model is None or self._ocr_model is None:
            self._load_models()
    
    def _load_models(self):
        """加载模型"""
        # 加载 YOLO 模型
        model_path = os.getenv('MODEL_PATH', './best.pt')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        self._yolo_model = YOLO(model_path)
        print(f"✅ YOLO 模型加载成功: {model_path}")
        
        # 初始化 PaddleOCR
        self._ocr_model = PaddleOCR(
            ocr_version="PP-OCRv5",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_thresh=0.01,
            text_det_box_thresh=0.01,
            text_rec_score_thresh=0.01,
        )
        print("✅ PaddleOCR 模型初始化成功")
    
    @property
    def yolo_model(self):
        """获取 YOLO 模型"""
        return self._yolo_model
    
    @property
    def ocr_model(self):
        """获取 OCR 模型"""
        return self._ocr_model


# 全局模型加载器实例
model_loader = ModelLoader()

