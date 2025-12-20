from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base


class Invoice(Base):
    """发票主表"""
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_name = Column(String(255), nullable=False, unique=True, comment='图片名称')
    detection_count = Column(Integer, nullable=False, comment='识别项数')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关联关系
    detections = relationship('Detection', back_populates='invoice', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, image_name='{self.image_name}', detection_count={self.detection_count})>"


class Detection(Base):
    """检测项表"""
    __tablename__ = 'detections'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False, comment='发票ID')
    class_name = Column(String(100), nullable=False, comment='类别名称')
    confidence = Column(Float, nullable=False, comment='置信度')
    extracted_text = Column(JSON, nullable=False, comment='提取的文本（字符串或字符串数组）')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    # 关联关系
    invoice = relationship('Invoice', back_populates='detections')
    
    def __repr__(self):
        return f"<Detection(id={self.id}, class_name='{self.class_name}', confidence={self.confidence})>"

