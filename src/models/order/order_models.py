from sqlalchemy import (
    Boolean, Column, Integer, SmallInteger, func, ForeignKey, Index,
    BigInteger,
    String, Text,
    DateTime,
)

from connection_module import Base


class Order(Base):
    __tablename__ = "order"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(String(length=36), unique=True, nullable=False)
    name = Column(String(length=50), unique=True, nullable=False)
    
    user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    user_uuid = Column(String(length=36), nullable=False)
    
    legal_entity_id = Column(Integer, ForeignKey("legal_entity.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    legal_entity_uuid = Column(String(length=36), nullable=False)
    directory_id = Column(BigInteger, ForeignKey("directory.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    directory_uuid = Column(String(length=36), nullable=False)
    
    type = Column(SmallInteger, ForeignKey("order_type.id", ondelete="CASCADE", onupdate="CASCADE"))
    data_id = Column(BigInteger, nullable=False)
    
    status = Column(SmallInteger, ForeignKey("order_status.id", ondelete="NO ACTION", onupdate="CASCADE"))
    
    can_be_updated_by_user = Column(Boolean, server_default="true")
    
    updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)

class OrderType(Base):
    __tablename__ = "order_type"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String, nullable=False)
    description = Column(Text)

class OrderStatus(Base):
    __tablename__ = "order_status"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
