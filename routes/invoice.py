"""
发票数据路由 - 发票查询相关接口
"""
from flask import Blueprint, request, jsonify
from db import SessionLocal
from model import Invoice

invoice_bp = Blueprint('invoice', __name__, url_prefix='/api/invoices')


@invoice_bp.route('', methods=['GET'])
def get_invoices():
    """获取发票列表"""
    db = SessionLocal()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 查询发票列表
        invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        total = db.query(Invoice).count()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': invoice.id,
                'image_name': invoice.image_name,
                'detection_count': invoice.detection_count,
                'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
                'updated_at': invoice.updated_at.isoformat() if invoice.updated_at else None
            } for invoice in invoices],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'查询失败: {str(e)}'}), 500
    finally:
        db.close()


@invoice_bp.route('/<int:invoice_id>', methods=['GET'])
def get_invoice_detail(invoice_id):
    """获取发票详情"""
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        if not invoice:
            return jsonify({'error': '发票不存在'}), 404
        
        # 将Invoice记录的所有字段转换为detections数组格式（保持API兼容性）
        detections_list = []
        # 定义所有字段名称（与CLASS_NAME_CN_MAP保持一致）
        field_names = [
            'quantity', 'unit_price', 'unit', 'item_name', 'check_code',
            'tax_amount', 'amount', 'tax_rate', 'specification',
            'invoice_number', 'invoice_code', 'invoice_date',
            'seller_name', 'buyer_name', 'seller_tax_id', 'buyer_tax_id',
            'seller_bank_account', 'buyer_bank_account',
            'seller_address_phone', 'buyer_address_phone',
            'total_amount'
        ]
        
        # 遍历所有字段，将非None的字段添加到detections列表
        for field_name in field_names:
            field_value = getattr(invoice, field_name, None)
            if field_value is not None:
                detections_list.append({
                    'class_name': field_name,
                    'extracted_text': field_value
                })
        
        return jsonify({
            'success': True,
            'data': {
                'id': invoice.id,
                'image_name': invoice.image_name,
                'detection_count': invoice.detection_count,
                'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
                'updated_at': invoice.updated_at.isoformat() if invoice.updated_at else None,
                'detections': detections_list
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'查询失败: {str(e)}'}), 500
    finally:
        db.close()

