from sqlalchemy import (
    Column, Integer, SmallInteger, Text, func, ForeignKey, Index,
    BigInteger,
    String,
    DateTime,
)

from connection_module import Base


class Chat(Base):
    __tablename__ = "chat"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    chat_subject_id = Column(SmallInteger, ForeignKey("chat_subject.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    subject_uuid = Column(String(length=36), unique=True, nullable=False)  # uuid сущности по которой он заведен (Контрагент, Заявки)
    
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)

class ChatSubject(Base):  # Контрагент, Заявка 
    __tablename__ = "chat_subject"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
    description = Column(Text)

class Message(Base):
    __tablename__ = "message"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    user_uuid = Column(String(length=36), nullable=False)
    user_privilege_id = Column(SmallInteger, ForeignKey("user_privilege.id", onupdate="CASCADE", ondelete="NO ACTION"), nullable=False)
    
    chat_id = Column(BigInteger, ForeignKey("chat.id", ondelete="CASCADE", onupdate="CASCADE"))
    
    data = Column(String(length=1000), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)
    
    __table_args__ = (
        Index("idx_message_chat", chat_id),
        Index("idx_message_user_uuid", user_uuid)
    ,)
