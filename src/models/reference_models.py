from sqlalchemy import (
    ForeignKey, UniqueConstraint, func,
    Column, 
    SmallInteger, Integer, BigInteger,
    DateTime,
    String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB

from connection_module import Base


class Country(Base):
    __tablename__ = "country"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(length=200))
    name_en_snake = Column(String(length=200))

class Currency(Base):
    __tablename__ = "currency"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    name = Column(String(length=100))
    letter_code = Column(String(length=10))
    number_code = Column(String(length=10))

class ErrLog(Base):
    __tablename__ = "errlog"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    endpoint = Column(String, nullable=False)
    params = Column(JSONB)
    msg = Column(Text)
    
    user_uuid = Column(String(length=36), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)

class ServiceNote(Base):
    __tablename__ = "service_note"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    subject_id = Column(SmallInteger, ForeignKey("service_note_subject.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=True)
    subject_uuid = Column(String(length=36), nullable=False)
    
    creator_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    creator_uuid = Column(String(length=36), nullable=False)
    
    title = Column(String(length=256), nullable=False)
    data = Column(String(length=512))
    
    updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('subject_id', 'subject_uuid', 'title', name='uq_subject_title'),
    )

class ServiceNoteSubject(Base):
    __tablename__ = "service_note_subject"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
    description = Column(Text)
