import re
from db import SessionLocal
from model import Invoice, Detection


# 类别名称到中文名称的映射
CLASS_NAME_CN_MAP = {
    "quantity": "数量",
    "unit_price": "单价",
    "unit": "单位",
    "item_name": "项目名称",
    "check_code": "校验码",
    "tax_amount": "税额",
    "amount": "金额",
    "tax_rate": "税率",
    "specification": "规格型号",
    "invoice_number": "发票号码",
    "invoice_code": "发票代码",
    "invoice_date": "开票日期",
    "seller_name": "销售方名称",
    "buyer_name": "购买方名称",
    "seller_tax_id": "销售方纳税人识别号",
    "buyer_tax_id": "购买方纳税人识别号",
    "seller_bank_account": "销售方开户行及账号",
    "buyer_bank_account": "购买方开户行及账号",
    "seller_address_phone": "销售方地址、电话",
    "buyer_address_phone": "购买方地址、电话",
    "total_amount": "价税合计",
}


def get_class_name_cn(class_name):
    """
    获取类别名称的中文名称
    
    Args:
        class_name: 类别名称（英文）
        
    Returns:
        str: 类别名称的中文名称，如果不存在则返回原名称
    """
    return CLASS_NAME_CN_MAP.get(class_name, class_name)


HEADER_KEYWORDS = {
    # 单位相关
    "unit": ["单", "位", "单位"],
    # 规格相关
    "specification": ["规", "格", "规格", "型", "号", "型号", "规格型号"],
    # 数量相关
    "quantity": ["数", "量", "数量"],
    # 单价相关
    "unit_price": ["单", "价", "单价"],
    # 金额相关
    "amount": ["金", "额", "金额"],
    # 税率相关
    "tax_rate": ["税", "率", "税率"],
    # 税额相关
    "tax_amount": ["税", "额", "税额"],
    # 货物名称相关
    "item_name": ["货", "物", "货物", "或", "应", "税", "劳", "务", "服务", "名称", "货物或应税劳务", "服务名称"],
}

def extract_values(text_list, class_name):
    """
    从文本中提取值

    Args:
        text: 输入文本

    Returns:
        tuple: 提取的数字和字母
    """
    if class_name in ["item_name"]:
        # 匹配以 * 开头和结尾的完整商品信息
        all_str = "".join(text.strip() for text in text_list[1:])
        count = 0
        res = []
        text = []
        for ch in all_str:
            if ch == "*":
                count += 1
                if count % 2 == 0:
                    text.append(":")
                else:
                    res.append("".join(text))
                    text.clear()
            else:
                text.append(ch)
        res.append("".join(text))
        return res[1:]

    elif class_name in ["invoice_number", "check_code", "invoice_code"]:
        # 使用正则表达式匹配连续的数字
        result = []
        for text in text_list:
            # 使用正则表达式匹配连续的数字
            numbers = re.findall(r'\d+', text)
            # 验证每个数字是否为20位
            for num in numbers:
                if len(num) == 20 or len(num) == 8 or len(num) == 12:
                    result.append(num)
        return result
    elif "invoice_date" == class_name:
        # 正则表达式匹配 xxxx年xx月xx日 格式
        pattern = r'\d{4}年\d{1,2}月\d{1,2}日'
        result = []
        for text in text_list:
            # 查找所有匹配的日期
            matches = re.findall(pattern, text)
            # 将匹配到的日期添加到结果中
            for match in matches:
                result.append(match)
        return result
    elif class_name in ["seller_name", "buyer_name", "seller_bank_account", "buyer_bank_account", "seller_address_phone", "buyer_address_phone"]:
        res = []
        find = False
        for text in text_list:
            if "：" in text or ":" in text:
                parts = text.split("：") if "：" in text else text.split(":")
                if len(parts) > 1:
                    res.append(parts[-1].strip())
                    find=True
            elif find and len(text.strip()) > 1:  # 排除单个字符（包括单个汉字）
                # 调试信息：确认条件满足
                print(f"DEBUG: 添加文本 '{text.strip()}', 长度={len(text.strip())}")
                res.append(text.strip())
        return " ".join(res)
    elif class_name in ["unit_price", "tax_amount", "tax_rate", "amount", "quantity", "total_amount"]:
        # 使用正则表达式匹配连续的数字
        result = []
        for text in text_list:
            # 匹配连续的数字，包括可能存在的小数点
            numbers = re.findall(r'(?:-)?\d+(?:\.\d+)?(?:%)?', text)
            # 移除空字符串并添加到结果中
            for num in numbers:
                if num:  # 确保不是空字符串
                    result.append(num)
        return result
    elif class_name in ["seller_tax_id", "buyer_tax_id"]:
        # 正则表达式模式：匹配连续18个字母或数字
        pattern = r'[a-zA-Z0-9]{18}'
        for text in text_list:
            matches = re.findall(pattern, text)
            if len(matches) > 0:
                return matches
        return None
    elif class_name in ["unit"]:
        res = []
        for text in text_list[1:]:
            if text.strip() not in HEADER_KEYWORDS["unit"]:
                res.append(text.strip())
        return res
    elif class_name in ["specification"]:
        return " ".join(text.strip() for text in text_list[1:])
    return None


def extract_text_from_bbox(ocr, image, bbox, class_name):
    """
    从边界框中提取文字（使用PaddleOCR）

    Args:
        image: 原始图像
        bbox: 边界框坐标 [x1, y1, x2, y2]

    Returns:
        str: 识别出的文字
    """
    x1, y1, x2, y2 = map(int, bbox)

    # 确保坐标在图像范围内
    x1 = max(0, min(x1, image.shape[1]))
    x2 = max(0, min(x2, image.shape[1]))
    y1 = max(0, min(y1, image.shape[0]))
    y2 = max(0, min(y2, image.shape[0]))

    # 裁剪边界框区域
    cropped_img = image[y1:y2, x1:x2]

    # 如果裁剪区域无效，则返回 None
    if cropped_img.size == 0:
        return None

    try:
        # 使用PaddleOCR进行文字识别
        result = ocr.predict(cropped_img)[0]

        # result.save_to_img("output")
        # result.save_to_json("output")
        extracted_text = extract_values(result["rec_texts"], class_name)
        # print(extracted_text)
        return extracted_text
    except Exception as e:
        print(f"PaddleOCR识别错误: {e}")
        return None


def save_to_database(detection_info):
    """
    将检测结果保存到数据库
    
    Args:
        detection_info: 包含检测结果的字典
    """
    db = SessionLocal()
    try:
        # 检查是否已存在相同 image_name 的记录
        existing_invoice = db.query(Invoice).filter(
            Invoice.image_name == detection_info['image_name']
        ).first()
        
        if existing_invoice:
            # 如果已存在，先删除旧的检测项
            db.query(Detection).filter(
                Detection.invoice_id == existing_invoice.id
            ).delete()
            # 更新发票信息
            existing_invoice.detection_count = detection_info['检测项数']
            invoice = existing_invoice
            print(f"更新数据库记录: {detection_info['image_name']}")
        else:
            # 创建新的发票记录
            invoice = Invoice(
                image_name=detection_info['image_name'],
                detection_count=detection_info['检测项数']
            )
            db.add(invoice)
            db.flush()  # 获取 invoice.id
            print(f"创建新数据库记录: {detection_info['image_name']}")
        
        # 保存检测项
        for detection_data in detection_info['detections']:
            # 处理 extracted_text：确保它是列表或字符串，不能是 None
            extracted_text = detection_data['extracted_text']
            if extracted_text is None:
                extracted_text = []  # 如果为 None，保存为空列表
            elif isinstance(extracted_text, str):
                extracted_text = [extracted_text]  # 如果是字符串，转换为列表
            # 如果已经是列表，保持不变
            
            # 获取类别名称的中文名称
            class_name = detection_data['class_name']
            class_name_cn = get_class_name_cn(class_name)
            
            detection = Detection(
                invoice_id=invoice.id,
                class_name=class_name,
                class_name_cn=class_name_cn,
                confidence=detection_data['confidence'],
                extracted_text=extracted_text
            )
            db.add(detection)
        
        # 提交事务
        db.commit()
        print(f"✅ 数据已成功保存到数据库 (ID: {invoice.id})")
        
    except Exception as e:
        # 发生错误时回滚
        db.rollback()
        print(f"❌ 保存到数据库失败: {e}")
        raise
    finally:
        db.close()