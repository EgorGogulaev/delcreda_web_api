from sqlalchemy import (
    Column, Integer, SmallInteger, Text, and_, func, ForeignKey, Index,
    BigInteger,
    String,
    Boolean,
    DateTime
)

from connection_module import Base


# Файл
class Document(Base):
    __tablename__ = "document"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(String(length=36), nullable=False, unique=True)
    
    name = Column(String(length=255), nullable=False)
    extansion = Column(String(length=6))
    size = Column(BigInteger)
    
    type = Column(SmallInteger, ForeignKey("document_type.id", ondelete="NO ACTION", onupdate="CASCADE"))
    
    directory_id = Column(BigInteger, ForeignKey("directory.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    directory_uuid = Column(String(length=36), nullable=False)
    path = Column(String, nullable=False)
    
    owner_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"))
    owner_user_uuid = Column(String(length=36))
    
    uploader_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    uploader_user_uuid = Column(String(length=36), nullable=False)
    
    visible = Column(Boolean, server_default="true", nullable=False)
    visibility_off_time = Column(DateTime(timezone=True))
    visibility_off_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"))
    visibility_off_user_uuid = Column(String(length=36))
    
    is_deleted = Column(Boolean, server_default="false")
    deleted_at = Column(DateTime(timezone=True))
    deleters_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"))
    deleters_user_uuid = Column(String(length=36))
    
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)
    
    __table_args__ = (
        Index("idx_document_uuid", uuid),
        Index("uix_directory_name_not_deleted", directory_uuid, name, unique=True, postgresql_where=and_(is_deleted == False))  # noqa: E712
    ,)

class DocumentType(Base):
    __tablename__ = "document_type"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
    description = Column(Text)

# Директрия
class Directory(Base):
    __tablename__ = "directory"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(String(length=36), nullable=False, unique=True)
    parent = Column(BigInteger, ForeignKey("directory.id", ondelete="NO ACTION", onupdate="CASCADE"))
    
    path = Column(String, nullable=False)
    type = Column(SmallInteger, ForeignKey("directory_type.id", ondelete="NO ACTION", onupdate="CASCADE"))
    
    owner_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"))
    owner_user_uuid = Column(String(length=36))
    
    uploader_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    uploader_user_uuid = Column(String(length=36), nullable=False)
    
    visible = Column(Boolean, server_default="true", nullable=False)
    visibility_off_time = Column(DateTime(timezone=True))
    visibility_off_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"))
    visibility_off_user_uuid = Column(String(length=36))
    
    is_deleted = Column(Boolean, server_default="false")
    deleted_at = Column(DateTime(timezone=True))
    deleters_user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"))
    deleters_user_uuid = Column(String(length=36))
    
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)

class DirectoryType(Base):
    __tablename__ = "directory_type"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
    description = Column(Text)
