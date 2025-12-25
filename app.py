"""
Flask 应用主文件
负责应用初始化和配置
"""
from flask import Flask
from db import init_db, engine
from sqlalchemy import inspect
from services.model_loader import model_loader
from services.invoice_service import InvoiceService
from routes.api import init_api_routes
from routes.invoice import invoice_bp
from routes.web import web_bp
from config import Config


def create_app():
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app(app)
    
    # 设置debug模式
    app.debug = app.config.get('DEBUG', False)
    
    # 初始化发票识别服务
    invoice_service = InvoiceService(
        yolo_model=model_loader.yolo_model,
        ocr_model=model_loader.ocr_model
    )
    
    # 注册蓝图
    app.register_blueprint(web_bp)
    app.register_blueprint(invoice_bp)
    
    # 初始化 API 路由（需要传入服务实例）
    api_bp = init_api_routes(invoice_service, app.config['ALLOWED_EXTENSIONS'])
    app.register_blueprint(api_bp)
    
    return app


def check_and_init_db():
    """检查数据库表是否存在，如果不存在则自动创建"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # 检查必要的表是否存在（现在只有一个invoices表）
    required_tables = ['invoices']
    missing_tables = [table for table in required_tables if table not in existing_tables]
    
    if missing_tables:
        print(f"检测到缺失的表: {missing_tables}")
        print("正在自动初始化数据库...")
        try:
            init_db()
            print("✅ 数据库初始化完成！")
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
            raise


# 创建应用实例
app = create_app()


if __name__ == '__main__':
    # 应用启动时检查并初始化数据库
    check_and_init_db()
    
    # 从配置中获取debug设置
    debug_mode = app.config.get('DEBUG', False)
    
    # 打印debug状态
    if debug_mode:
        print("🔧 Debug模式已开启")
        print("   - 自动重载: 开启")
        print("   - 详细错误信息: 开启")
        print("   - 调试器: 开启")
    else:
        print("⚙️  Debug模式已关闭")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
