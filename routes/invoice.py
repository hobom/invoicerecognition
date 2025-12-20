"""
发票数据路由 - 发票查询相关接口
"""
from flask import Blueprint, request, jsonify
from db import SessionLocal
from model import Invoice, Detection

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
        
        detections = db.query(Detection).filter(
            Detection.invoice_id == invoice_id
        ).all()
        
        return jsonify({
            'success': True,
            'data': {
                'id': invoice.id,
                'image_name': invoice.image_name,
                'detection_count': invoice.detection_count,
                'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
                'updated_at': invoice.updated_at.isoformat() if invoice.updated_at else None,
                'detections': [{
                    'id': det.id,
                    'class_name': det.class_name,
                    'confidence': det.confidence,
                    'extracted_text': det.extracted_text
                } for det in detections]
            }
        }), 200
    except Exception as e:
        return jsonify({'error': f'查询失败: {str(e)}'}), 500
    finally:
        db.close()

