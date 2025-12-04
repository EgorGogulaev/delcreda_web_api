from sqlalchemy import (
    Column, Integer, SmallInteger, func, ForeignKey, Index,
    BigInteger,
    String, Text,
    DateTime,
)

from connection_module import Base



class CommercialProposal(Base):
    __tablename__ = "commercial_proposal"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    uuid = Column(String(length=36), unique=True, nullable=False)
    name = Column(String(length=50), unique=True, nullable=False)
    
    user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    user_uuid = Column(String(length=36), nullable=False)
    
    counterparty_id = Column(Integer, ForeignKey("counterparty.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=True)
    counterparty_uuid = Column(String(length=36), nullable=True)
    
    directory_id = Column(BigInteger, ForeignKey("directory.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    directory_uuid = Column(String(length=36), nullable=False)
    
    type = Column(SmallInteger, ForeignKey("commercial_proposal_type.id", ondelete="CASCADE", onupdate="CASCADE"))
    data_id = Column(BigInteger, nullable=False)
    
    status = Column(SmallInteger, ForeignKey("application_status.id", ondelete="NO ACTION", onupdate="CASCADE"))
    
    updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)

class CommercialProposalType(Base):
    __tablename__ = "commercial_proposal_type"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
    description = Column(Text)

class CommercialProposalStatus(Base):
    __tablename__ = "commercial_proposal_status"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
    description = Column(Text)
