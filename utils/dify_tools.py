"""
Dify工作流工具函数
用于Dify等工作流框架调用SQL执行和发票核验功能
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# API基础URL（如果部署在本地，使用本地地址；如果部署在服务器，使用服务器地址）
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')


def execute_sql(sql: str) -> dict:
    """
    执行SQL查询（供Dify工作流调用）
    
    Args:
        sql: SQL语句
        
    Returns:
        dict: 执行结果
            {
                "result": "查询结果或错误信息"
            }
    """
    url = f"{API_BASE_URL}/api/execute"
    
    payload = {
        "sql": sql
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                if result.get('type') == 'select':
                    return {
                        "result": f"查询成功，共{result.get('count', 0)}条记录：{result.get('data', [])}"
                }
                else:
                    return {
                        "result": f"操作成功，影响{result.get('affected_rows', 0)}行"
                    }
            else:
                return {
                    "result": f"执行失败：{result.get('error', '未知错误')}"
                }
        else:
            return {
                "result": f"请求失败，状态码：{response.status_code}，响应：{response.text}"
            }
    except requests.exceptions.RequestException as e:
        return {
            "result": f"请求异常：{str(e)}"
        }


def check_invoice(invoice_number: str, invoice_date: str, invoice_amount: str) -> dict:
    """
    核验发票（供Dify工作流调用）
    
    Args:
        invoice_number: 发票号码
        invoice_date: 开票日期 (YYYY-MM-DD)
        invoice_amount: 价税合计
        
    Returns:
        dict: 核验结果
            {
                "result": "核验结果或错误信息"
            }
    """
    url = f"{API_BASE_URL}/api/check"
    
    payload = {
        "fphm": invoice_number,
        "kprq": invoice_date,
        "jshj": invoice_amount
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return {
                    "result": f"核验成功：{result.get('result', '')}"
                }
            else:
                return {
                    "result": f"核验失败：{result.get('error', '未知错误')}"
                }
        else:
            return {
                "result": f"请求失败，状态码：{response.status_code}，响应：{response.text}"
            }
    except requests.exceptions.RequestException as e:
        return {
            "result": f"请求异常：{str(e)}"
        }
