# predict.py
import json
import os
from pathlib import Path

from ultralytics import YOLO
import cv2
import numpy as np
from paddleocr import PaddleOCR
from utils import extract_text_from_bbox, save_to_database


def main(img_path, model, ocr):
    """
    处理单个图像文件

    Args:
        img_path: 图像文件路径
        model: YOLO 模型实例
        ocr: PaddleOCR 实例
    """
    # 检查图像文件是否存在
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"图像文件不存在: {img_path}")
    
    # 对图像进行预测
    results = model.predict(
        source=img_path,
        save=False,
        show=False,
        conf=0.1,
        iou=0.1,
        imgsz=640,
    )

    # 读取原始图像用于OCR
    original_image = cv2.imread(img_path)
    if original_image is None:
        raise ValueError(f"无法读取图像文件: {img_path}")

    detection_info = {
        "image_name": Path(img_path).stem,
        "检测项数": 0,
        "detections": []
    }

    # 打印预测结果并进行OCR识别
    for result in results:
        if result.boxes:
            for i, box in enumerate(result.boxes):
                class_name = result.names[int(box.cls)]
                confidence = box.conf.item()
                bbox_coords = box.xyxy.tolist()[0]

                extracted_text = extract_text_from_bbox(ocr, original_image, bbox_coords, class_name)

                # 修复 None 检查逻辑
                if extracted_text is None or (isinstance(extracted_text, list) and len(extracted_text) == 0):
                    extracted_text = None

                if class_name not in ["buyer", "seller"]:
                    detection = {
                        "class_name": class_name,
                        "confidence": confidence,
                        "extracted_text": extracted_text,
                    }
                    detection_info["detections"].append(detection)
                    detection_info["检测项数"] += 1

    # 确保输出目录存在
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # 保存 JSON 文件
    output_path = output_dir / f"{detection_info['image_name']}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(detection_info, f, ensure_ascii=False, indent=4)
    print(f"已保存结果到 {output_path}")
    
    # 保存到数据库
    save_to_database(detection_info)


if __name__ == '__main__':
    # 初始化PaddleOCR
    ocr = PaddleOCR(
        ocr_version="PP-OCRv5",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_det_thresh=0.01,
        text_det_box_thresh=0.01,
        text_rec_score_thresh=0.01,
    )  # 通过 ocr_version 参数来使用 PP-OCR 其他版本

    # 加载训练好的模型
    model_path = "./best.pt"
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"模型文件不存在: {model_path}")
    model = YOLO(model_path)  # 使用训练好的权重文件

    # 处理图像
    img_path = "invoice_00001.jpg"
    main(img_path, model, ocr)


