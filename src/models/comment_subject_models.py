from sqlalchemy import (
    Column, ForeignKey, UniqueConstraint, func,
    SmallInteger, BigInteger,
    DateTime, String,
)

from connection_module import Base


class CommentSubject(Base):
    __tablename__ = "comment_subject"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    subject_id = Column(SmallInteger, ForeignKey("chat_subject.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    subject_uuid = Column(String(length=36), nullable=False)
    
    creator_uuid = Column(String(length=36), nullable=False)
    last_updater_uuid = Column(String(length=36))
    
    data = Column(String)
    
    updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('subject_id', 'subject_uuid', name='uq_comment_subject_id_uuid'),
    )
