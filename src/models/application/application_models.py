from sqlalchemy import (
    Boolean, Column, Integer, SmallInteger, func, ForeignKey, Index,
    BigInteger,
    String, Text,
    DateTime,
)

from connection_module import Base


class Application(Base):
    __tablename__ = "application"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(String(length=36), unique=True, nullable=False)
    name = Column(String(length=50), unique=True, nullable=False)
    
    user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    user_uuid = Column(String(length=36), nullable=False)
    
    counterparty_id = Column(Integer, ForeignKey("counterparty.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    counterparty_uuid = Column(String(length=36), nullable=False)
    
    directory_id = Column(BigInteger, ForeignKey("directory.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    directory_uuid = Column(String(length=36), nullable=False)
    
    type = Column(SmallInteger, ForeignKey("application_type.id", ondelete="CASCADE", onupdate="CASCADE"))
    data_id = Column(BigInteger, nullable=False)
    
    status = Column(SmallInteger, ForeignKey("application_status.id", ondelete="NO ACTION", onupdate="CASCADE"))
    
    can_be_updated_by_user = Column(Boolean, server_default="true")
    
    updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)

class ApplicationType(Base):
    __tablename__ = "application_type"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String, nullable=False)
    description = Column(Text)

class ApplicationStatus(Base):
    __tablename__ = "application_status"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
