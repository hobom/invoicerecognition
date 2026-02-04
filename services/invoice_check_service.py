"""
发票核验服务
提供发票真伪核验功能，调用外部API
"""
import urllib.parse
import urllib3
import os
from dotenv import load_dotenv

load_dotenv()

# 阿里云发票核验API配置
INVOICE_CHECK_CONFIG = {
    'host': 'https://fapiao.market.alicloudapi.com',
    'path': '/v2/invoice/query',
    'appcode': os.getenv('ALIYUN_APPCODE', '628ee87f1f1f4589b637a0af7042a128')  # 从环境变量读取，有默认值
}


class InvoiceCheckService:
    """发票核验服务类"""
    
    @staticmethod
    def check_invoice(invoice_number: str, invoice_date: str, invoice_amount: str):
        """
        核验发票真伪
        
        Args:
            invoice_number: 发票号码 (fphm)
            invoice_date: 开票日期 (kprq)，格式：YYYY-MM-DD
            invoice_amount: 价税合计 (jshj)
            
        Returns:
            dict: 核验结果
                - success: 是否成功
                - result: API返回的原始结果（JSON字符串）
                - error: 错误信息（如果有）
        """
        # 校验必填参数
        if not all([invoice_number, invoice_date, invoice_amount]):
            return {
                'success': False,
                'error': '缺少必填参数：发票号码(fphm)、开票日期(kprq)、价税合计(jshj)'
            }
        
        try:
            # 构造请求URL
            url = INVOICE_CHECK_CONFIG['host'] + INVOICE_CHECK_CONFIG['path']
            
            # 构造请求参数
            bodys = {
                'fphm': invoice_number,
                'kprq': invoice_date,
                'jshj': invoice_amount
            }
            post_data = urllib.parse.urlencode(bodys).encode('utf-8')
            
            # 发送POST请求
            http = urllib3.PoolManager()
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Authorization': 'APPCODE ' + INVOICE_CHECK_CONFIG['appcode']
            }
            
            response = http.request('POST', url, body=post_data, headers=headers)
            
            # 解析响应
            result_text = response.data.decode('utf-8')
            
            return {
                'success': True,
                'status_code': response.status,
                'result': result_text
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'核验请求失败: {str(e)}'
            }
    
    @staticmethod
    def check_invoice_from_db(invoice_id: int):
        """
        从数据库读取发票信息并核验
        
        Args:
            invoice_id: 发票ID
            
        Returns:
            dict: 核验结果
        """
        from db import SessionLocal
        from model import Invoice
        
        db = SessionLocal()
        try:
            invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if not invoice:
                return {
                    'success': False,
                    'error': '发票不存在'
                }
            
            # 提取核验所需字段（JSON字段可能是字符串、数字或列表）
            def extract_json_value(value):
                """从JSON字段中提取实际值"""
                if value is None:
                    return None
                if isinstance(value, list):
                    # 如果是列表，取第一个元素
                    return value[0] if value else None
                return value
            
            invoice_number = extract_json_value(invoice.invoice_number)
            invoice_date = extract_json_value(invoice.invoice_date)
            invoice_amount = extract_json_value(invoice.total_amount)
            
            # 检查字段是否完整
            if not invoice_number or not invoice_date or not invoice_amount:
                return {
                    'success': False,
                    'error': '发票信息不完整，缺少发票号码、开票日期或价税合计'
                }
            
            # 转换为字符串并格式化
            invoice_number = str(invoice_number).strip()
            
            # 格式化日期（确保为YYYY-MM-DD格式）
            date_str = str(invoice_date).strip()
            # 如果日期格式不是YYYY-MM-DD，尝试转换（这里简化处理，实际可能需要更复杂的解析）
            
            # 格式化金额（确保为字符串，精确到两位小数）
            try:
                if isinstance(invoice_amount, (int, float)):
                    amount_str = f"{float(invoice_amount):.2f}"
                else:
                    # 尝试转换为数字
                    amount_float = float(str(invoice_amount).replace(',', '').strip())
                    amount_str = f"{amount_float:.2f}"
            except (ValueError, TypeError):
                amount_str = str(invoice_amount).strip()
            
            # 调用核验API
            return InvoiceCheckService.check_invoice(
                invoice_number=invoice_number,
                invoice_date=date_str,
                invoice_amount=amount_str
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'数据库查询失败: {str(e)}'
            }
        finally:
            db.close()
