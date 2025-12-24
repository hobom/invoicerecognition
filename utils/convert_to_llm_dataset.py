"""
将当前项目的发票识别数据转换为多模态大模型微调格式
支持转换为LLaVA/Qwen-VL等模型的训练格式
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到路径，以便导入模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 类别名称到中文名称的映射（与utils/utils.py中的保持一致）
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


def convert_detection_to_text(detections: List[Dict]) -> str:
    """
    将检测结果转换为自然语言文本
    
    Args:
        detections: 检测结果列表
        
    Returns:
        str: 格式化的文本输出
    """
    result_lines = []
    
    for detection in detections:
        class_name = detection.get('class_name', '')
        extracted_text = detection.get('extracted_text', None)
        confidence = detection.get('confidence', 0)
        
        if extracted_text is None:
            continue
        
        # 获取中文字段名
        field_name = CLASS_NAME_CN_MAP.get(class_name, class_name)
        
        # 处理提取的文本
        if isinstance(extracted_text, list):
            if len(extracted_text) > 0:
                # 如果是列表，合并或选择第一个
                text_value = extracted_text[0] if len(extracted_text) == 1 else ', '.join(str(x) for x in extracted_text if x)
            else:
                continue
        else:
            text_value = str(extracted_text)
        
        if text_value:
            result_lines.append(f"{field_name}：{text_value}")
    
    return "\n".join(result_lines)


def create_instruction_variants(class_name_cn_map: Dict[str, str]) -> List[str]:
    """
    创建多样化的指令模板
    
    Args:
        class_name_cn_map: 类别名称到中文的映射
        
    Returns:
        List[str]: 指令列表
    """
    instructions = [
        "请提取这张发票的所有关键信息。",
        "请识别并提取发票中的以下字段：发票代码、发票号码、开票日期、销售方名称、购买方名称、金额、税额等。",
        "从这张发票图片中提取所有可见的字段信息。",
        "请详细提取发票的各项信息，包括基础信息、主体信息和金额信息。",
        "识别这张发票并提取所有字段值。",
        "请提取发票的关键字段，包括发票代码、号码、日期、销售方、购买方、商品信息、金额等。",
        "从发票中提取所有结构化信息。",
    ]
    return instructions


def convert_json_to_llm_format(
    json_path: Path,
    image_path: Path,
    output_format: str = "llava",  # "llava" or "qwen-vl"
    use_variants: bool = True
) -> List[Dict[str, Any]]:
    """
    将单个JSON文件转换为大模型训练格式
    
    Args:
        json_path: JSON文件路径
        image_path: 对应的图像文件路径
        output_format: 输出格式 ("llava" 或 "qwen-vl")
        use_variants: 是否使用指令变体（数据增强）
        
    Returns:
        List[Dict]: 转换后的数据列表（如果使用变体，可能返回多条）
    """
    # 读取JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 转换为文本输出
    detections = data.get('detections', [])
    output_text = convert_detection_to_text(detections)
    
    if not output_text:
        return []
    
    # 获取图像路径（相对路径或绝对路径）
    image_path_str = str(image_path.absolute())
    
    # 创建指令
    if use_variants:
        instructions = create_instruction_variants(CLASS_NAME_CN_MAP)
    else:
        instructions = ["请提取这张发票的所有关键信息。"]
    
    results = []
    for instruction in instructions:
        if output_format == "llava":
            # LLaVA格式
            result = {
                "id": f"{data.get('image_name', 'unknown')}_{len(results)}",
                "image": image_path_str,
                "conversations": [
                    {
                        "from": "human",
                        "value": f"<image>\n{instruction}"
                    },
                    {
                        "from": "gpt",
                        "value": output_text
                    }
                ]
            }
        elif output_format == "qwen-vl":
            # Qwen-VL格式
            result = {
                "id": f"{data.get('image_name', 'unknown')}_{len(results)}",
                "image": image_path_str,
                "conversation": [
                    {
                        "from": "user",
                        "value": [
                            {
                                "image": image_path_str
                            },
                            {
                                "text": instruction
                            }
                        ]
                    },
                    {
                        "from": "assistant",
                        "value": output_text
                    }
                ]
            }
        else:
            # 通用格式
            result = {
                "id": f"{data.get('image_name', 'unknown')}_{len(results)}",
                "image": image_path_str,
                "instruction": instruction,
                "output": output_text
            }
        
        results.append(result)
    
    return results


def batch_convert(
    json_dir: Path,
    image_dir: Path,
    output_file: Path,
    output_format: str = "llava",
    use_variants: bool = True
):
    """
    批量转换JSON文件为大模型训练格式
    
    Args:
        json_dir: JSON文件目录
        image_dir: 图像文件目录
        output_file: 输出文件路径（JSONL格式）
        output_format: 输出格式
        use_variants: 是否使用指令变体
    """
    json_files = list(json_dir.glob("*.json"))
    total_records = 0
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for json_file in json_files:
            # 尝试找到对应的图像文件
            image_name = json_file.stem
            # 尝试多种可能的图像文件名
            possible_image_names = [
                image_name,
                image_name.replace('invoice_invoice_', 'invoice_'),
                image_name.replace('invoice_', ''),
            ]
            
            image_path = None
            for name in possible_image_names:
                for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                    potential_path = image_dir / f"{name}{ext}"
                    if potential_path.exists():
                        image_path = potential_path
                        break
                if image_path:
                    break
            
            if not image_path:
                print(f"⚠️  未找到图像文件: {json_file.stem}")
                continue
            
            # 转换数据
            try:
                records = convert_json_to_llm_format(
                    json_file,
                    image_path,
                    output_format=output_format,
                    use_variants=use_variants
                )
                
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    total_records += 1
                
                print(f"✅ 已转换: {json_file.name} -> {len(records)} 条记录")
            except Exception as e:
                print(f"❌ 转换失败 {json_file.name}: {e}")
    
    print(f"\n✅ 转换完成！共生成 {total_records} 条训练数据")
    print(f"📁 输出文件: {output_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='将发票识别数据转换为大模型训练格式')
    parser.add_argument('--json_dir', type=str, default='output', help='JSON文件目录')
    parser.add_argument('--image_dir', type=str, default='uploads', help='图像文件目录')
    parser.add_argument('--output', type=str, default='llm_training_data.jsonl', help='输出文件路径')
    parser.add_argument('--format', type=str, default='llava', choices=['llava', 'qwen-vl', 'general'], 
                       help='输出格式: llava, qwen-vl, general')
    parser.add_argument('--no-variants', action='store_true', help='不使用指令变体（不进行数据增强）')
    
    args = parser.parse_args()
    
    json_dir = Path(args.json_dir)
    image_dir = Path(args.image_dir)
    output_file = Path(args.output)
    
    if not json_dir.exists():
        print(f"❌ JSON目录不存在: {json_dir}")
        return
    
    if not image_dir.exists():
        print(f"❌ 图像目录不存在: {image_dir}")
        return
    
    batch_convert(
        json_dir=json_dir,
        image_dir=image_dir,
        output_file=output_file,
        output_format=args.format,
        use_variants=not args.no_variants
    )


if __name__ == '__main__':
    main()

