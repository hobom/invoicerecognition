"""
SQL执行和发票核验路由
整合 execute_sql 项目的功能
"""
from flask import Blueprint, request, jsonify
from services.sql_service import SQLService
from services.invoice_check_service import InvoiceCheckService

sql_bp = Blueprint('sql', __name__, url_prefix='/api')


@sql_bp.route('/execute', methods=['POST'])
def execute_sql():
    """
    执行SQL查询接口
    
    请求体（JSON）:
    {
        "sql": "SELECT * FROM invoices LIMIT 10"
    }
    
    返回:
    {
        "success": true,
        "type": "select" | "dml",
        "data": [...],  // SELECT查询时返回结果集
        "count": 10,    // SELECT查询时返回记录数
        "affected_rows": 5  // DML操作时返回受影响行数
    }
    """
    try:
        data = request.get_json()
        if not data or 'sql' not in data:
            return jsonify({
                'success': False,
                'error': 'SQL语句是必需的，请提供sql字段'
            }), 400
        
        sql = data['sql']
        if not sql or not sql.strip():
            return jsonify({
                'success': False,
                'error': 'SQL语句不能为空'
            }), 400
        
        # 执行SQL
        result = SQLService.execute_query(sql)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'执行SQL失败: {str(e)}'
        }), 500


@sql_bp.route('/check', methods=['POST'])
def check_invoice():
    """
    发票核验接口
    
    支持两种请求方式：
    1. form-data (application/x-www-form-urlencoded):
       - fphm: 发票号码
       - kprq: 开票日期 (YYYY-MM-DD)
       - jshj: 价税合计
    
    2. JSON (application/json):
       {
         "fphm": "发票号码",
         "kprq": "2024-01-01",
         "jshj": "1000.00"
       }
    
    返回:
    {
        "success": true,
        "status_code": 200,
        "result": "API返回的原始结果（JSON字符串）"
    }
    """
    try:
        # 支持form-data和JSON两种方式
        if request.is_json:
            data = request.get_json()
            invoice_number = data.get('fphm')
            invoice_date = data.get('kprq')
            invoice_amount = data.get('jshj')
        else:
            invoice_number = request.form.get('fphm')
            invoice_date = request.form.get('kprq')
            invoice_amount = request.form.get('jshj')
        
        # 校验必填参数
        if not all([invoice_number, invoice_date, invoice_amount]):
            return jsonify({
                'success': False,
                'error': '缺少必填参数，请提供fphm(发票号码)、kprq(开票日期)、jshj(价税合计)'
            }), 400
        
        # 调用核验服务
        result = InvoiceCheckService.check_invoice(
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            invoice_amount=invoice_amount
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'核验失败: {str(e)}'
        }), 500


@sql_bp.route('/check/<int:invoice_id>', methods=['POST'])
def check_invoice_by_id(invoice_id):
    """
    根据发票ID核验发票
    
    Args:
        invoice_id: 发票ID（从数据库invoices表查询）
    
    返回:
    {
        "success": true,
        "status_code": 200,
        "result": "API返回的原始结果"
    }
    """
    try:
        result = InvoiceCheckService.check_invoice_from_db(invoice_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404 if '不存在' in result.get('error', '') else 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'核验失败: {str(e)}'
        }), 500
