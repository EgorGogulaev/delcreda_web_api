
from sqlalchemy import (
    Column, Integer, SmallInteger, Text, func, ForeignKey,
    Boolean, 
    BigInteger,
    String,
    DateTime,
)

from connection_module import Base


class Notification(Base):
    __tablename__ = "notification"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(String(length=36), unique=True, nullable=False)
    
    for_admin = Column(Boolean, nullable=False)
    subject_id = Column(SmallInteger, ForeignKey("notification_subject.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=True)
    subject_uuid = Column(String(length=36))
    
    initiator_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    initiator_user_uuid = Column(String(length=36), nullable=False)
    
    recipient_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"))
    recipient_user_uuid = Column(String(length=36))
    
    data = Column(String(length=512), nullable=False)
    
    is_read = Column(Boolean, server_default="false", nullable=False)
    read_at = Column(DateTime(timezone=True))
    
    is_important = Column(Boolean, nullable=False)
    time_importance_change = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)

class NotificationSubject(Base):
    __tablename__ = "notification_subject"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
    description = Column(Text)
