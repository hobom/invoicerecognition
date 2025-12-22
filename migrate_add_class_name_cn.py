"""
数据库迁移脚本：为detections表添加class_name_cn字段
"""
from db import engine, SessionLocal
from sqlalchemy import text


def migrate_add_class_name_cn():
    """
    为detections表添加class_name_cn字段
    如果字段已存在，则跳过
    """
    db = SessionLocal()
    try:
        # 检查字段是否已存在
        check_sql = """
        SELECT COUNT(*) as count
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'detections'
        AND COLUMN_NAME = 'class_name_cn'
        """
        
        result = db.execute(text(check_sql))
        count = result.fetchone()[0]
        
        if count > 0:
            print("✅ class_name_cn 字段已存在，跳过迁移")
            return
        
        # 添加新字段
        alter_sql = """
        ALTER TABLE detections
        ADD COLUMN class_name_cn VARCHAR(100) NULL COMMENT '类别名称（中文）'
        AFTER class_name
        """
        
        db.execute(text(alter_sql))
        db.commit()
        print("✅ 成功添加 class_name_cn 字段")
        
        # 更新现有数据的中文名称
        from utils.utils import get_class_name_cn
        from model import Detection
        
        detections = db.query(Detection).all()
        updated_count = 0
        for detection in detections:
            if not detection.class_name_cn:
                detection.class_name_cn = get_class_name_cn(detection.class_name)
                updated_count += 1
        
        if updated_count > 0:
            db.commit()
            print(f"✅ 已更新 {updated_count} 条现有记录的中文名称")
        else:
            print("ℹ️  没有需要更新的现有记录")
            
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    print("开始数据库迁移：添加 class_name_cn 字段")
    migrate_add_class_name_cn()
    print("迁移完成！")

