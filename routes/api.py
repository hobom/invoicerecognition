"""
API 路由 - 发票识别相关接口
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename
from pathlib import Path
import json
import time
from services.invoice_service import InvoiceService

api_bp = Blueprint('api', __name__, url_prefix='/api')


def init_api_routes(invoice_service: InvoiceService, allowed_extensions):
    """
    初始化 API 路由
    
    Args:
        invoice_service: 发票识别服务实例
        allowed_extensions: 允许的文件扩展名集合
    """
    
    def allowed_file(filename):
        """检查文件扩展名是否允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in allowed_extensions
    
    @api_bp.route('/health', methods=['GET'])
    def health_check():
        """健康检查接口"""
        return jsonify({
            'status': 'ok',
            'message': '服务运行正常'
        })
    
    @api_bp.route('/predict', methods=['POST'])
    def predict():
        """
        发票识别接口
        
        支持多种方式：
        1. 单文件上传：使用 multipart/form-data，字段名为 'file'
        2. 多文件上传：使用 multipart/form-data，字段名为 'files[]'
        3. 文件夹路径：使用 JSON 请求，字段名为 'folder_path'
        4. 文件路径列表：使用 JSON 请求，字段名为 'image_paths'
        5. 单文件路径：使用 JSON 请求，字段名为 'image_path'
        """
        try:
            save_json = request.form.get('save_json', request.json.get('save_json', True) if request.is_json else 'true')
            save_db = request.form.get('save_db', request.json.get('save_db', True) if request.is_json else 'true')
            save_json = str(save_json).lower() == 'true' if isinstance(save_json, str) else bool(save_json)
            save_db = str(save_db).lower() == 'true' if isinstance(save_db, str) else bool(save_db)
            
            # 方式1：多文件上传
            if 'files[]' in request.files:
                files = request.files.getlist('files[]')
                if not files or all(f.filename == '' for f in files):
                    return jsonify({'error': '未选择文件'}), 400
                
                # 保存所有文件并处理
                upload_dir = Path("uploads")
                upload_dir.mkdir(exist_ok=True)
                
                file_paths = []
                for file in files:
                    if file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = upload_dir / filename
                        file.save(str(file_path))
                        file_paths.append(str(file_path))
                
                if not file_paths:
                    return jsonify({'error': '没有有效的图像文件'}), 400
                
                # 批量处理
                results = invoice_service.process_batch(file_paths, save_json, save_db)
                
                return jsonify({
                    'success': True,
                    'total': len(results),
                    'success_count': sum(1 for r in results if r['success']),
                    'failed_count': sum(1 for r in results if not r['success']),
                    'data': results
                }), 200
            
            # 方式2：单文件上传
            elif 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': '未选择文件'}), 400
                
                if not allowed_file(file.filename):
                    return jsonify({'error': '不支持的文件格式'}), 400
                
                # 处理上传的文件
                result = invoice_service.process_uploaded_file(
                    file,
                    save_json=save_json,
                    save_db=save_db
                )
                
                return jsonify({
                    'success': True,
                    'data': result
                }), 200
            
            # 方式3：JSON 请求
            elif request.is_json:
                data = request.get_json()
                
                # 处理文件夹
                if 'folder_path' in data:
                    folder_path = data['folder_path']
                    results = invoice_service.process_folder(
                        folder_path,
                        save_json=save_json,
                        save_db=save_db
                    )
                    
                    return jsonify({
                        'success': True,
                        'total': len(results),
                        'success_count': sum(1 for r in results if r['success']),
                        'failed_count': sum(1 for r in results if not r['success']),
                        'data': results
                    }), 200
                
                # 处理文件路径列表
                elif 'image_paths' in data:
                    image_paths = data['image_paths']
                    if not isinstance(image_paths, list):
                        return jsonify({'error': 'image_paths 必须是数组'}), 400
                    
                    results = invoice_service.process_batch(
                        image_paths,
                        save_json=save_json,
                        save_db=save_db
                    )
                    
                    return jsonify({
                        'success': True,
                        'total': len(results),
                        'success_count': sum(1 for r in results if r['success']),
                        'failed_count': sum(1 for r in results if not r['success']),
                        'data': results
                    }), 200
                
                # 处理单个文件路径
                elif 'image_path' in data:
                    image_path = data['image_path']
                    result = invoice_service.process_image(
                        image_path,
                        save_json=save_json,
                        save_db=save_db
                    )
                    
                    return jsonify({
                        'success': True,
                        'data': result
                    }), 200
                
                else:
                    return jsonify({'error': '请提供 file、files[]、folder_path、image_paths 或 image_path 参数'}), 400
            
            else:
                return jsonify({'error': '请提供文件或 JSON 数据'}), 400
        
        except FileNotFoundError as e:
            return jsonify({'error': str(e)}), 404
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f'处理失败: {str(e)}'}), 500
    
    @api_bp.route('/predict/stream', methods=['POST'])
    def predict_stream():
        """
        发票识别接口（支持进度更新）
        使用 Server-Sent Events (SSE) 实时推送处理进度
        
        支持：
        1. 多文件上传：使用 multipart/form-data，字段名为 'files[]'
        2. 文件路径列表：使用 JSON 请求，字段名为 'image_paths'
        3. 文件夹路径：使用 JSON 请求，字段名为 'folder_path'
        """
        def generate():
            try:
                save_json = request.form.get('save_json', request.json.get('save_json', True) if request.is_json else 'true')
                save_db = request.form.get('save_db', request.json.get('save_db', True) if request.is_json else 'true')
                save_json = str(save_json).lower() == 'true' if isinstance(save_json, str) else bool(save_json)
                save_db = str(save_db).lower() == 'true' if isinstance(save_db, str) else bool(save_db)
                
                file_paths = []
                results = []
                
                # 方式1：多文件上传
                if 'files[]' in request.files:
                    files = request.files.getlist('files[]')
                    if not files or all(f.filename == '' for f in files):
                        yield f"data: {json.dumps({'type': 'error', 'message': '未选择文件'}, ensure_ascii=False)}\n\n"
                        return
                    
                    upload_dir = Path("uploads")
                    upload_dir.mkdir(exist_ok=True)
                    
                    for file in files:
                        if file.filename and allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            file_path = upload_dir / filename
                            file.save(str(file_path))
                            file_paths.append(str(file_path))
                    
                    if not file_paths:
                        yield f"data: {json.dumps({'type': 'error', 'message': '没有有效的图像文件'}, ensure_ascii=False)}\n\n"
                        return
                
                # 方式2：JSON 请求
                elif request.is_json:
                    data = request.get_json()
                    
                    if 'folder_path' in data:
                        folder_path = data['folder_path']
                        folder = Path(folder_path)
                        if not folder.exists() or not folder.is_dir():
                            yield f"data: {json.dumps({'type': 'error', 'message': f'文件夹不存在: {folder_path}'}, ensure_ascii=False)}\n\n"
                            return
                        
                        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.PNG', '.JPG', '.JPEG', '.GIF', '.BMP'}
                        file_paths = [str(f) for f in folder.iterdir() 
                                     if f.is_file() and f.suffix in image_extensions]
                        
                        if not file_paths:
                            yield f"data: {json.dumps({'type': 'error', 'message': '文件夹中没有找到图像文件'}, ensure_ascii=False)}\n\n"
                            return
                    
                    elif 'image_paths' in data:
                        image_paths = data['image_paths']
                        if not isinstance(image_paths, list):
                            yield f"data: {json.dumps({'type': 'error', 'message': 'image_paths 必须是数组'}, ensure_ascii=False)}\n\n"
                            return
                        file_paths = image_paths
                    
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'message': '请提供 files[]、image_paths 或 folder_path 参数'}, ensure_ascii=False)}\n\n"
                        return
                
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': '请提供文件或 JSON 数据'}, ensure_ascii=False)}\n\n"
                    return
                
                # 发送开始消息
                total = len(file_paths)
                yield f"data: {json.dumps({'type': 'start', 'total': total}, ensure_ascii=False)}\n\n"
                
                # 批量处理，实时发送进度更新
                for idx, img_path in enumerate(file_paths, 1):
                    try:
                        # 发送开始处理消息
                        yield f"data: {json.dumps({'type': 'progress', 'current': idx, 'total': total, 'percent': int((idx / total) * 100), 'file': Path(img_path).name, 'status': 'processing'}, ensure_ascii=False)}\n\n"
                        
                        result = invoice_service.process_image(img_path, save_json, save_db)
                        results.append({
                            'success': True,
                            'file': img_path,
                            'result': result,
                            'index': idx,
                            'total': total
                        })
                        
                        # 发送成功消息
                        yield f"data: {json.dumps({'type': 'progress', 'current': idx, 'total': total, 'percent': int((idx / total) * 100), 'file': Path(img_path).name, 'status': 'success'}, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        results.append({
                            'success': False,
                            'file': img_path,
                            'error': str(e),
                            'index': idx,
                            'total': total
                        })
                        
                        # 发送失败消息
                        yield f"data: {json.dumps({'type': 'progress', 'current': idx, 'total': total, 'percent': int((idx / total) * 100), 'file': Path(img_path).name, 'status': 'failed', 'error': str(e)}, ensure_ascii=False)}\n\n"
                
                # 发送完成消息
                yield f"data: {json.dumps({'type': 'complete', 'total': len(results), 'success_count': sum(1 for r in results if r['success']), 'failed_count': sum(1 for r in results if not r['success']), 'data': results}, ensure_ascii=False)}\n\n"
            
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'处理失败: {str(e)}'}, ensure_ascii=False)}\n\n"
        
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    
    return api_bp

