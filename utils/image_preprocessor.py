"""
图像预处理模块 - 使用PaddlePaddle进行图像旋转、透视变换、文字水平调整
"""
import cv2
import numpy as np
from paddleocr import PaddleOCR
from typing import Tuple, Optional


class ImagePreprocessor:
    """图像预处理器类"""
    
    def __init__(self, enable_ocr_preprocess: bool = True):
        """
        初始化图像预处理器
        
        Args:
            enable_ocr_preprocess: 是否启用OCR预处理（用于文字方向检测）
        """
        self.enable_ocr_preprocess = enable_ocr_preprocess
        if enable_ocr_preprocess:
            # 初始化PaddleOCR用于文字方向检测
            self.ocr = PaddleOCR(
                use_angle_cls=True,  # 启用文字方向分类
                lang='ch',  # 中文
                # show_log=False
            )
    
    def detect_text_orientation(self, image: np.ndarray) -> int:
        """
        检测图像中文字的方向角度
        
        Args:
            image: 输入图像 (BGR格式)
            
        Returns:
            int: 旋转角度 (0, 90, 180, 270)
        """
        if not self.enable_ocr_preprocess:
            return 0
        
        try:
            # 使用PaddleOCR检测文字方向（启用方向分类）
            result = self.ocr.ocr(image, cls=True)
            
            if not result or not result[0]:
                return 0
            
            # 分析文字行的角度
            # 通过计算文字行的主要方向来判断图像旋转角度
            angles = []
            for line in result[0]:
                if line and len(line) >= 2:
                    # 获取文字框坐标
                    box = line[0]  # 四个角点坐标
                    if len(box) == 4:
                        # 计算文字行的角度
                        # 使用左上和右上两个点计算角度
                        pt1 = np.array(box[0])
                        pt2 = np.array(box[1])
                        # 计算角度（以度为单位）
                        angle_rad = np.arctan2(pt2[1] - pt1[1], pt2[0] - pt1[0])
                        angle_deg = np.degrees(angle_rad)
                        angles.append(angle_deg)
            
            if not angles:
                return 0
            
            # 计算平均角度
            avg_angle = np.mean(angles)
            
            # 将角度标准化到0-360范围
            normalized = int(avg_angle) % 360
            if normalized < 0:
                normalized += 360
            
            # 映射到最近的标准角度
            if normalized < 45 or normalized >= 315:
                return 0
            elif 45 <= normalized < 135:
                return 90
            elif 135 <= normalized < 225:
                return 180
            else:
                return 270
                
        except Exception as e:
            print(f"文字方向检测失败: {e}")
            # 如果检测失败，尝试使用图像本身的特征
            return self._detect_orientation_by_image_features(image)
    
    def _detect_orientation_by_image_features(self, image: np.ndarray) -> int:
        """
        通过图像特征检测方向（备用方法）
        
        Args:
            image: 输入图像
            
        Returns:
            int: 旋转角度 (0, 90, 180, 270)
        """
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # 使用投影法检测文字方向
            # 水平投影：统计每行的非零像素数
            h_projection = np.sum(gray > 127, axis=1)
            # 垂直投影：统计每列的非零像素数
            v_projection = np.sum(gray > 127, axis=0)
            
            # 计算投影的方差（文字行应该在一个方向上更集中）
            h_variance = np.var(h_projection)
            v_variance = np.var(v_projection)
            
            # 如果水平投影方差更大，说明文字是水平的（0度）
            # 如果垂直投影方差更大，说明文字是垂直的（90度或270度）
            if h_variance > v_variance * 1.5:
                return 0  # 水平文字
            elif v_variance > h_variance * 1.5:
                # 需要进一步判断是90度还是270度
                # 简单判断：如果图像高度大于宽度，可能是90度
                if image.shape[0] > image.shape[1]:
                    return 90
                else:
                    return 270
            else:
                return 0
        except Exception as e:
            print(f"基于图像特征的方向检测失败: {e}")
            return 0
    
    def rotate_image(self, image: np.ndarray, angle: int) -> np.ndarray:
        """
        旋转图像到指定角度
        
        Args:
            image: 输入图像
            angle: 旋转角度 (0, 90, 180, 270)
            
        Returns:
            np.ndarray: 旋转后的图像
        """
        if angle == 0:
            return image
        
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        if angle == 90:
            # 顺时针旋转90度
            matrix = cv2.getRotationMatrix2D(center, -90, 1.0)
            new_w, new_h = h, w
        elif angle == 180:
            # 旋转180度
            matrix = cv2.getRotationMatrix2D(center, 180, 1.0)
            new_w, new_h = w, h
        elif angle == 270:
            # 顺时针旋转270度（或逆时针90度）
            matrix = cv2.getRotationMatrix2D(center, -270, 1.0)
            new_w, new_h = h, w
        else:
            return image
        
        # 调整旋转矩阵以适应新的图像尺寸
        matrix[0, 2] += (new_w / 2) - center[0]
        matrix[1, 2] += (new_h / 2) - center[1]
        
        rotated = cv2.warpAffine(image, matrix, (new_w, new_h), 
                                 flags=cv2.INTER_LINEAR, 
                                 borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=(255, 255, 255))
        
        return rotated
    
    def auto_rotate_image(self, image: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        自动检测并旋转图像，使文字水平
        
        Args:
            image: 输入图像
            
        Returns:
            Tuple[np.ndarray, int]: (旋转后的图像, 旋转角度)
        """
        angle = self.detect_text_orientation(image)
        rotated_image = self.rotate_image(image, angle)
        return rotated_image, angle
    
    def detect_document_corners(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        检测文档的四个角点（用于透视变换）
        
        Args:
            image: 输入图像
            
        Returns:
            Optional[np.ndarray]: 四个角点坐标，形状为 (4, 2)，如果检测失败返回None
        """
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 高斯模糊
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 边缘检测
        edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
        
        # 形态学操作，连接边缘
        kernel = np.ones((5, 5), np.uint8)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # 找到最大的轮廓
        largest_contour = max(contours, key=cv2.contourArea)
        
        # 计算轮廓的近似多边形
        epsilon = 0.02 * cv2.arcLength(largest_contour, True)
        approx = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        # 如果找到4个点，返回这些点
        if len(approx) == 4:
            # 将点排序为：左上、右上、右下、左下
            points = approx.reshape(4, 2)
            return self._order_points(points)
        
        # 如果没找到4个点，尝试使用凸包
        hull = cv2.convexHull(largest_contour)
        epsilon = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)
        
        if len(approx) >= 4:
            # 选择最大的4个点
            points = approx.reshape(-1, 2)
            # 使用边界框的四个角点
            rect = cv2.minAreaRect(points)
            box = cv2.boxPoints(rect)
            return self._order_points(box)
        
        return None
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """
        将四个点排序为：左上、右上、右下、左下
        
        Args:
            pts: 四个点的坐标，形状为 (4, 2)
            
        Returns:
            np.ndarray: 排序后的点
        """
        # 初始化坐标点
        rect = np.zeros((4, 2), dtype="float32")
        
        # 计算点的和与差
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        
        # 左上角点：和最小
        rect[0] = pts[np.argmin(s)]
        # 右下角点：和最大
        rect[2] = pts[np.argmax(s)]
        # 右上角点：差最小
        rect[1] = pts[np.argmin(diff)]
        # 左下角点：差最大
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def perspective_transform(self, image: np.ndarray, 
                             corners: Optional[np.ndarray] = None,
                             target_width: Optional[int] = None,
                             target_height: Optional[int] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        对图像进行透视变换，校正文档
        
        Args:
            image: 输入图像
            corners: 四个角点坐标，如果为None则自动检测
            target_width: 目标宽度，如果为None则使用原图宽度
            target_height: 目标高度，如果为None则使用原图高度
            
        Returns:
            Tuple[np.ndarray, Optional[np.ndarray]]: (变换后的图像, 使用的角点坐标)
        """
        # 如果没有提供角点，自动检测
        if corners is None:
            corners = self.detect_document_corners(image)
        
        if corners is None:
            # 如果检测失败，返回原图
            return image, None
        
        # 计算目标尺寸
        if target_width is None or target_height is None:
            # 计算原始文档的宽度和高度
            (tl, tr, br, bl) = corners
            
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))
            
            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))
            
            target_width = target_width if target_width else maxWidth
            target_height = target_height if target_height else maxHeight
        
        # 定义目标矩形的四个角点
        dst = np.array([
            [0, 0],
            [target_width - 1, 0],
            [target_width - 1, target_height - 1],
            [0, target_height - 1]
        ], dtype="float32")
        
        # 计算透视变换矩阵
        M = cv2.getPerspectiveTransform(corners, dst)
        
        # 应用透视变换
        warped = cv2.warpPerspective(image, M, (target_width, target_height),
                                    flags=cv2.INTER_LINEAR,
                                    borderMode=cv2.BORDER_CONSTANT,
                                    borderValue=(255, 255, 255))
        
        return warped, corners
    
    def correct_text_orientation(self, image: np.ndarray) -> np.ndarray:
        """
        校正文字方向，使文字水平
        
        Args:
            image: 输入图像
            
        Returns:
            np.ndarray: 校正后的图像
        """
        # 使用PaddleOCR检测文字方向
        angle = self.detect_text_orientation(image)
        
        # 如果检测到需要旋转，进行旋转
        if angle != 0:
            image = self.rotate_image(image, angle)
        
        return image
    
    def preprocess(self, image: np.ndarray, 
                  enable_rotation: bool = True,
                  enable_perspective: bool = True,
                  enable_text_correction: bool = True) -> np.ndarray:
        """
        完整的图像预处理流程
        
        Args:
            image: 输入图像
            enable_rotation: 是否启用旋转调整
            enable_perspective: 是否启用透视变换
            enable_text_correction: 是否启用文字水平调整
            
        Returns:
            np.ndarray: 预处理后的图像
        """
        processed_image = image.copy()
        
        # 步骤1: 透视变换（在校正文字方向之前进行，因为透视变换可能改变图像方向）
        if enable_perspective:
            try:
                processed_image, corners = self.perspective_transform(processed_image)
                if corners is not None:
                    print("✅ 已应用透视变换")
            except Exception as e:
                print(f"⚠️ 透视变换失败: {e}")
        
        # 步骤2: 文字方向校正
        if enable_text_correction:
            try:
                processed_image = self.correct_text_orientation(processed_image)
                print("✅ 已校正文字方向")
            except Exception as e:
                print(f"⚠️ 文字方向校正失败: {e}")
        
        # 步骤3: 旋转调整（如果需要额外的旋转）
        if enable_rotation:
            try:
                processed_image, angle = self.auto_rotate_image(processed_image)
                if angle != 0:
                    print(f"✅ 已旋转图像 {angle} 度")
            except Exception as e:
                print(f"⚠️ 旋转调整失败: {e}")
        
        return processed_image

