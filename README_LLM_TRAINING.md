# 发票识别数据转换为大模型训练格式

本工具可以将当前项目生成的发票识别数据转换为多模态大模型（如LLaVA、Qwen-VL）的训练格式。

## 功能特点

1. **自动数据转换**：将YOLO+PaddleOCR的识别结果转换为大模型训练所需的图文配对格式
2. **多格式支持**：支持LLaVA、Qwen-VL等主流多模态模型的训练格式
3. **数据增强**：自动生成多样化的指令变体，提升模型泛化能力
4. **批量处理**：支持批量转换所有JSON文件

## 使用方法

### 基本用法

```bash
# 转换所有数据为LLaVA格式（默认）
python utils/convert_to_llm_dataset.py

# 指定输出格式
python utils/convert_to_llm_dataset.py --format qwen-vl

# 不使用指令变体（每条数据只生成一条训练样本）
python utils/convert_to_llm_dataset.py --no-variants

# 自定义路径
python utils/convert_to_llm_dataset.py \
    --json_dir output \
    --image_dir uploads \
    --output llm_training_data.jsonl
```

### 参数说明

- `--json_dir`: JSON文件目录（默认：`output`）
- `--image_dir`: 图像文件目录（默认：`uploads`）
- `--output`: 输出文件路径（默认：`llm_training_data.jsonl`）
- `--format`: 输出格式，可选：`llava`、`qwen-vl`、`general`（默认：`llava`）
- `--no-variants`: 不使用指令变体（不进行数据增强）

## 输出格式

### LLaVA格式

```json
{
  "id": "invoice_00001_0",
  "image": "/path/to/image.jpg",
  "conversations": [
    {
      "from": "human",
      "value": "<image>\n请提取这张发票的所有关键信息。"
    },
    {
      "from": "gpt",
      "value": "发票代码：037022100211\n发票号码：14892315\n开票日期：2022年01月10日\n..."
    }
  ]
}
```

### Qwen-VL格式

```json
{
  "id": "invoice_00001_0",
  "image": "/path/to/image.jpg",
  "conversation": [
    {
      "from": "user",
      "value": [
        {"image": "/path/to/image.jpg"},
        {"text": "请提取这张发票的所有关键信息。"}
      ]
    },
    {
      "from": "assistant",
      "value": "发票代码：037022100211\n发票号码：14892315\n..."
    }
  ]
}
```

## 数据质量评估

### 当前项目数据的优势

1. ✅ **结构化数据**：已有准确的字段标注和提取结果
2. ✅ **图像资源**：原始发票图像完整保存
3. ✅ **字段覆盖**：覆盖发票的主要字段（代码、号码、日期、金额等）
4. ✅ **数据量**：已有一定数量的标注数据

### 需要注意的问题

1. ⚠️ **数据准确性**：需要人工校验提取结果的准确性
2. ⚠️ **数据量**：建议至少1000+条高质量数据用于微调
3. ⚠️ **数据多样性**：需要包含不同类型的发票（专用发票、普通发票、电子发票等）
4. ⚠️ **错误处理**：当前数据中可能包含OCR识别错误，需要清洗

## 数据清洗建议

在转换为训练数据前，建议进行以下清洗：

1. **验证字段格式**：检查发票代码、号码等是否符合规范
2. **去除低质量数据**：删除置信度过低或字段缺失过多的记录
3. **人工校验**：对关键字段进行人工抽样校验
4. **数据平衡**：确保不同类型发票的数据量相对均衡

## 微调流程

1. **数据准备**：使用本工具转换数据格式
2. **数据清洗**：去除低质量数据，人工校验
3. **数据增强**：可结合图像预处理（旋转、透视变换）生成更多变体
4. **模型选择**：选择合适的多模态模型（Qwen-VL-7B、LLaVA-7B等）
5. **微调训练**：使用LoRA/QLoRA进行高效微调
6. **模型评估**：在测试集上评估模型效果

## 示例：完整微调流程

```bash
# 1. 转换数据
python utils/convert_to_llm_dataset.py --format llava --output train_data.jsonl

# 2. 数据清洗（需要自定义脚本）
python scripts/clean_training_data.py --input train_data.jsonl --output clean_train_data.jsonl

# 3. 数据分割
python scripts/split_dataset.py --input clean_train_data.jsonl --train 0.8 --val 0.1 --test 0.1

# 4. 微调训练（使用LLaVA框架）
# 参考：https://github.com/haotian-liu/LLaVA
```

## 注意事项

1. **图像路径**：确保转换后的JSONL文件中的图像路径在训练环境中可访问
2. **数据格式**：不同框架可能需要不同的数据格式，请根据实际使用的框架调整
3. **内存占用**：如果数据量很大，建议分批处理
4. **版本兼容**：确保转换工具与训练框架的版本兼容

## 后续优化

1. 添加数据质量评估指标
2. 支持更多模型格式（GPT-4V、Gemini等）
3. 集成数据清洗工具
4. 支持自动数据增强（图像变换）

