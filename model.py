from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from db import Base


class Invoice(Base):
    """发票表 - 合并了原Invoice和Detection表的所有字段"""
    __tablename__ = 'invoices'
    
    # 主键和基础字段
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_name = Column(String(255), nullable=False, unique=True, comment='图片名称')
    detection_count = Column(Integer, nullable=False, comment='识别项数')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 基础信息字段
    invoice_code = Column(JSON, nullable=True, comment='发票代码')
    invoice_number = Column(JSON, nullable=True, comment='发票号码')
    invoice_date = Column(JSON, nullable=True, comment='开票日期')
    
    # 销售方信息字段
    seller_name = Column(JSON, nullable=True, comment='销售方名称')
    seller_tax_id = Column(JSON, nullable=True, comment='销售方纳税人识别号')
    seller_bank_account = Column(JSON, nullable=True, comment='销售方开户行及账号')
    seller_address_phone = Column(JSON, nullable=True, comment='销售方地址、电话')
    
    # 购买方信息字段
    buyer_name = Column(JSON, nullable=True, comment='购买方名称')
    buyer_tax_id = Column(JSON, nullable=True, comment='购买方纳税人识别号')
    buyer_bank_account = Column(JSON, nullable=True, comment='购买方开户行及账号')
    buyer_address_phone = Column(JSON, nullable=True, comment='购买方地址、电话')
    
    # 商品信息字段
    item_name = Column(JSON, nullable=True, comment='项目名称')
    specification = Column(JSON, nullable=True, comment='规格型号')
    unit = Column(JSON, nullable=True, comment='单位')
    quantity = Column(JSON, nullable=True, comment='数量')
    unit_price = Column(JSON, nullable=True, comment='单价')
    amount = Column(JSON, nullable=True, comment='金额')
    tax_rate = Column(JSON, nullable=True, comment='税率')
    tax_amount = Column(JSON, nullable=True, comment='税额')
    
    # 合计信息字段
    total_amount = Column(JSON, nullable=True, comment='价税合计')
    check_code = Column(JSON, nullable=True, comment='校验码')
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, image_name='{self.image_name}', detection_count={self.detection_count})>"

