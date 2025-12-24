"""
发票识别服务 - 处理发票识别的业务逻辑
"""
import json
import os
from pathlib import Path
import cv2
from utils import extract_text_from_bbox, save_to_database
from utils.image_preprocessor import ImagePreprocessor


class InvoiceService:
    """发票识别服务类"""
    
    def __init__(self, yolo_model, ocr_model, enable_preprocessing: bool = False):
        """
        初始化服务
        
        Args:
            yolo_model: YOLO 模型实例
            ocr_model: PaddleOCR 模型实例
            enable_preprocessing: 是否启用图像预处理
        """
        self.yolo_model = yolo_model
        self.ocr_model = ocr_model
        self.enable_preprocessing = enable_preprocessing
        if enable_preprocessing:
            self.preprocessor = ImagePreprocessor(enable_ocr_preprocess=True)
        else:
            self.preprocessor = None
    
    def process_image(self, img_path, save_json=True, save_db=True, 
                     enable_rotation=True, enable_perspective=True, enable_text_correction=True):
        """
        处理单个图像文件
        
        Args:
            img_path: 图像文件路径
            save_json: 是否保存 JSON 文件
            save_db: 是否保存到数据库
            enable_rotation: 是否启用旋转调整
            enable_perspective: 是否启用透视变换
            enable_text_correction: 是否启用文字水平调整
            
        Returns:
            dict: 检测结果
        """
        # 检查图像文件是否存在
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"图像文件不存在: {img_path}")
        
        # 读取原始图像
        original_image = cv2.imread(img_path)
        if original_image is None:
            raise ValueError(f"无法读取图像文件: {img_path}")
        
        # 图像预处理
        if self.enable_preprocessing and self.preprocessor:
            print(f"🔄 开始预处理图像: {img_path}")
            processed_image = self.preprocessor.preprocess(
                original_image,
                enable_rotation=enable_rotation,
                enable_perspective=enable_perspective,
                enable_text_correction=enable_text_correction
            )
            # 保存预处理后的图像到临时文件，用于YOLO预测
            temp_path = str(Path(img_path).parent / f"temp_{Path(img_path).name}")
            cv2.imwrite(temp_path, processed_image)
            predict_source = temp_path
        else:
            processed_image = original_image
            predict_source = img_path
        
        # 对图像进行预测
        results = self.yolo_model.predict(
            source=predict_source,
            save=False,
            show=False,
            conf=0.1,
            iou=0.1,
            imgsz=640,
        )
        
        # 使用预处理后的图像进行OCR（如果进行了预处理）
        ocr_image = processed_image if self.enable_preprocessing else original_image
        
        # 清理临时文件
        if self.enable_preprocessing and self.preprocessor and predict_source != img_path:
            try:
                if os.path.exists(predict_source):
                    os.remove(predict_source)
            except Exception as e:
                print(f"⚠️ 清理临时文件失败: {e}")
        
        detection_info = {
            "image_name": Path(img_path).stem,
            "检测项数": 0,
            "detections": []
        }
        
        # 处理预测结果并进行OCR识别
        for result in results:
            if result.boxes:
                for box in result.boxes:
                    class_name = result.names[int(box.cls)]
                    confidence = box.conf.item()
                    bbox_coords = box.xyxy.tolist()[0]
                    
                    extracted_text = extract_text_from_bbox(
                        self.ocr_model, 
                        ocr_image, 
                        bbox_coords, 
                        class_name
                    )
                    
                    # 处理 None 或空列表
                    if extracted_text is None or (isinstance(extracted_text, list) and len(extracted_text) == 0):
                        extracted_text = None
                    
                    # 排除 buyer 和 seller 类别
                    if class_name not in ["buyer", "seller"]:
                        detection = {
                            "class_name": class_name,
                            "confidence": confidence,
                            "extracted_text": extracted_text,
                        }
                        detection_info["detections"].append(detection)
                        detection_info["检测项数"] += 1
        
        # 保存 JSON 文件
        if save_json:
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{detection_info['image_name']}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(detection_info, f, ensure_ascii=False, indent=4)
            print(f"已保存结果到 {output_path}")
        
        # 保存到数据库
        if save_db:
            save_to_database(detection_info)
        
        return detection_info
    
    def process_uploaded_file(self, file, save_json=True, save_db=True):
        """
        处理上传的文件
        
        Args:
            file: Flask 上传的文件对象
            save_json: 是否保存 JSON 文件
            save_db: 是否保存到数据库
            
        Returns:
            dict: 检测结果
        """
        # 创建临时目录
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # 保存上传的文件
        filename = file.filename
        file_path = upload_dir / filename
        file.save(str(file_path))
        
        try:
            # 处理图像
            result = self.process_image(str(file_path), save_json, save_db)
            return result
        finally:
            # 可选：处理完后删除临时文件
            # os.remove(file_path)
            pass
    
    def process_batch(self, file_paths, save_json=True, save_db=True, progress_callback=None):
        """
        批量处理多个图像文件
        
        Args:
            file_paths: 图像文件路径列表
            save_json: 是否保存 JSON 文件
            save_db: 是否保存到数据库
            progress_callback: 进度回调函数，接收 (current, total, file_path, status) 参数
            
        Returns:
            list: 检测结果列表，每个元素包含 (success, result/error)
        """
        results = []
        total = len(file_paths)
        
        for idx, img_path in enumerate(file_paths, 1):
            try:
                # 通知进度：开始处理
                if progress_callback:
                    progress_callback(idx, total, img_path, 'processing')
                
                result = self.process_image(img_path, save_json, save_db)
                results.append({
                    'success': True,
                    'file': img_path,
                    'result': result,
                    'index': idx,
                    'total': total
                })
                
                # 通知进度：处理成功
                if progress_callback:
                    progress_callback(idx, total, img_path, 'success')
            except Exception as e:
                results.append({
                    'success': False,
                    'file': img_path,
                    'error': str(e),
                    'index': idx,
                    'total': total
                })
                
                # 通知进度：处理失败
                if progress_callback:
                    progress_callback(idx, total, img_path, 'failed', str(e))
        
        return results
    
    def process_folder(self, folder_path, save_json=True, save_db=True, progress_callback=None):
        """
        处理文件夹中的所有图像文件
        
        Args:
            folder_path: 文件夹路径
            save_json: 是否保存 JSON 文件
            save_db: 是否保存到数据库
            progress_callback: 进度回调函数
            
        Returns:
            list: 检测结果列表
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"文件夹不存在或不是目录: {folder_path}")
        
        # 支持的图像格式
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.PNG', '.JPG', '.JPEG', '.GIF', '.BMP'}
        
        # 获取所有图像文件
        image_files = [str(f) for f in folder.iterdir() 
                      if f.is_file() and f.suffix in image_extensions]
        
        if not image_files:
            raise ValueError(f"文件夹中没有找到图像文件: {folder_path}")
        
        return self.process_batch(image_files, save_json, save_db, progress_callback)

