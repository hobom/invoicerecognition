"""
数据库迁移脚本：将invoices和detections两个表合并为一个invoices表

旧结构：
  - invoices表：id, image_name, detection_count, created_at, updated_at
  - detections表：id, invoice_id, created_at, updated_at, 以及所有18个字段

新结构：
  - invoices表：包含原invoices和detections表的所有字段

使用方法：
    python migrate_merge_tables.py
"""
from db import SessionLocal, engine
from sqlalchemy import text
import sys


def migrate_merge_tables():
    """
    合并invoices和detections表
    """
    db = SessionLocal()
    try:
        print("开始合并invoices和detections表...")
        
        # 检查表是否存在
        inspector = __import__('sqlalchemy').inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if 'invoices' not in existing_tables:
            print("⚠️  invoices表不存在，无需迁移")
            return
        
        # 检查是否已经是新结构（检查invoices表是否有invoice_code字段）
        columns = [col['name'] for col in inspector.get_columns('invoices')]
        
        if 'invoice_code' in columns:
            print("✅ invoices表已经是新结构，无需迁移")
            # 如果detections表还存在，删除它
            if 'detections' in existing_tables:
                print("删除旧的detections表...")
                db.execute(text("DROP TABLE IF EXISTS detections;"))
                db.commit()
                print("✅ 已删除旧的detections表")
            return
        
        if 'detections' not in existing_tables:
            print("⚠️  detections表不存在，但invoices表也不是新结构")
            print("   请检查数据库状态")
            return
        
        print("检测到旧表结构，开始迁移...")
        
        # 1. 备份旧表
        print("步骤1: 备份旧表...")
        db.execute(text("CREATE TABLE invoices_backup LIKE invoices;"))
        db.execute(text("INSERT INTO invoices_backup SELECT * FROM invoices;"))
        db.execute(text("CREATE TABLE detections_backup LIKE detections;"))
        db.execute(text("INSERT INTO detections_backup SELECT * FROM detections;"))
        db.commit()
        print("✅ 备份完成")
        
        # 2. 创建新表结构
        print("步骤2: 创建新表结构...")
        db.execute(text("CREATE TABLE invoices_new LIKE invoices;"))
        
        # 添加所有字段列
        db.execute(text("""
            ALTER TABLE invoices_new
            ADD COLUMN invoice_code JSON NULL COMMENT '发票代码',
            ADD COLUMN invoice_number JSON NULL COMMENT '发票号码',
            ADD COLUMN invoice_date JSON NULL COMMENT '开票日期',
            ADD COLUMN seller_name JSON NULL COMMENT '销售方名称',
            ADD COLUMN seller_tax_id JSON NULL COMMENT '销售方纳税人识别号',
            ADD COLUMN seller_bank_account JSON NULL COMMENT '销售方开户行及账号',
            ADD COLUMN seller_address_phone JSON NULL COMMENT '销售方地址、电话',
            ADD COLUMN buyer_name JSON NULL COMMENT '购买方名称',
            ADD COLUMN buyer_tax_id JSON NULL COMMENT '购买方纳税人识别号',
            ADD COLUMN buyer_bank_account JSON NULL COMMENT '购买方开户行及账号',
            ADD COLUMN buyer_address_phone JSON NULL COMMENT '购买方地址、电话',
            ADD COLUMN item_name JSON NULL COMMENT '项目名称',
            ADD COLUMN specification JSON NULL COMMENT '规格型号',
            ADD COLUMN unit JSON NULL COMMENT '单位',
            ADD COLUMN quantity JSON NULL COMMENT '数量',
            ADD COLUMN unit_price JSON NULL COMMENT '单价',
            ADD COLUMN amount JSON NULL COMMENT '金额',
            ADD COLUMN tax_rate JSON NULL COMMENT '税率',
            ADD COLUMN tax_amount JSON NULL COMMENT '税额',
            ADD COLUMN total_amount JSON NULL COMMENT '价税合计',
            ADD COLUMN check_code JSON NULL COMMENT '校验码';
        """))
        db.commit()
        print("✅ 新表结构创建成功")
        
        # 3. 迁移数据
        print("步骤3: 迁移数据...")
        
        # 获取所有发票
        invoices = db.execute(text("SELECT id, image_name, detection_count, created_at, updated_at FROM invoices;")).fetchall()
        migrated_count = 0
        
        for invoice in invoices:
            invoice_id = invoice.id
            
            # 获取该发票的检测数据（可能有多行，取第一行或合并）
            detections = db.execute(text("""
                SELECT invoice_code, invoice_number, invoice_date,
                       seller_name, seller_tax_id, seller_bank_account, seller_address_phone,
                       buyer_name, buyer_tax_id, buyer_bank_account, buyer_address_phone,
                       item_name, specification, unit, quantity, unit_price,
                       amount, tax_rate, tax_amount, total_amount, check_code
                FROM detections
                WHERE invoice_id = :invoice_id
                LIMIT 1
            """), {'invoice_id': invoice_id}).fetchone()
            
            # 构建插入语句
            if detections:
                # 有检测数据，合并插入
                db.execute(text("""
                    INSERT INTO invoices_new 
                    (id, image_name, detection_count, created_at, updated_at,
                     invoice_code, invoice_number, invoice_date,
                     seller_name, seller_tax_id, seller_bank_account, seller_address_phone,
                     buyer_name, buyer_tax_id, buyer_bank_account, buyer_address_phone,
                     item_name, specification, unit, quantity, unit_price,
                     amount, tax_rate, tax_amount, total_amount, check_code)
                    VALUES 
                    (:id, :image_name, :detection_count, :created_at, :updated_at,
                     :invoice_code, :invoice_number, :invoice_date,
                     :seller_name, :seller_tax_id, :seller_bank_account, :seller_address_phone,
                     :buyer_name, :buyer_tax_id, :buyer_bank_account, :buyer_address_phone,
                     :item_name, :specification, :unit, :quantity, :unit_price,
                     :amount, :tax_rate, :tax_amount, :total_amount, :check_code)
                """), {
                    'id': invoice.id,
                    'image_name': invoice.image_name,
                    'detection_count': invoice.detection_count,
                    'created_at': invoice.created_at,
                    'updated_at': invoice.updated_at,
                    'invoice_code': detections.invoice_code,
                    'invoice_number': detections.invoice_number,
                    'invoice_date': detections.invoice_date,
                    'seller_name': detections.seller_name,
                    'seller_tax_id': detections.seller_tax_id,
                    'seller_bank_account': detections.seller_bank_account,
                    'seller_address_phone': detections.seller_address_phone,
                    'buyer_name': detections.buyer_name,
                    'buyer_tax_id': detections.buyer_tax_id,
                    'buyer_bank_account': detections.buyer_bank_account,
                    'buyer_address_phone': detections.buyer_address_phone,
                    'item_name': detections.item_name,
                    'specification': detections.specification,
                    'unit': detections.unit,
                    'quantity': detections.quantity,
                    'unit_price': detections.unit_price,
                    'amount': detections.amount,
                    'tax_rate': detections.tax_rate,
                    'tax_amount': detections.tax_amount,
                    'total_amount': detections.total_amount,
                    'check_code': detections.check_code
                })
            else:
                # 没有检测数据，只插入基础信息
                db.execute(text("""
                    INSERT INTO invoices_new 
                    (id, image_name, detection_count, created_at, updated_at)
                    VALUES 
                    (:id, :image_name, :detection_count, :created_at, :updated_at)
                """), {
                    'id': invoice.id,
                    'image_name': invoice.image_name,
                    'detection_count': invoice.detection_count,
                    'created_at': invoice.created_at,
                    'updated_at': invoice.updated_at
                })
            
            migrated_count += 1
        
        db.commit()
        print(f"✅ 已迁移 {migrated_count} 条发票记录")
        
        # 4. 替换旧表
        print("步骤4: 替换旧表...")
        db.execute(text("DROP TABLE invoices;"))
        db.execute(text("DROP TABLE detections;"))
        db.execute(text("RENAME TABLE invoices_new TO invoices;"))
        db.commit()
        
        print("✅ 迁移完成！")
        print(f"   共迁移 {migrated_count} 条发票记录")
        print("   备份表: invoices_backup, detections_backup")
        print("   如需恢复，请手动从备份表恢复数据")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  数据已备份到 invoices_backup 和 detections_backup 表")
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    print("=" * 60)
    print("合并invoices和detections表迁移脚本")
    print("=" * 60)
    print()
    print("⚠️  警告：此操作将修改数据库表结构")
    print("   建议在执行前备份数据库")
    print("   脚本会自动创建备份表: invoices_backup, detections_backup")
    print()
    
    response = input("是否继续？(yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("已取消迁移")
        sys.exit(0)
    
    migrate_merge_tables()

