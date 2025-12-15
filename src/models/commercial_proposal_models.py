from sqlalchemy import (
    Boolean, Column, Integer, SmallInteger, func, ForeignKey, Index,
    BigInteger,
    String, Text,
    DateTime,
)

from connection_module import Base



class CommercialProposal(Base):
    __tablename__ = "commercial_proposal"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    uuid = Column(String(length=36), unique=True, nullable=False)
    appliaction_name = Column(String(length=50), unique=True, nullable=False)  # номер завки на КП (бизнес направление, контрагент, порядковый номер заяки, год)
    commercial_proposal_name = Column(String(length=50), nullable=True)
    type = Column(SmallInteger, ForeignKey("commercial_proposal_type.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)  # тип КП
    
    # Пользователь к кому относится КП
    user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    user_uuid = Column(String(length=36), nullable=False)
    
    # к чему привязка? Если только к Контрагенту - КП верхнеуровневое...
    counterparty_id = Column(Integer, ForeignKey("counterparty.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=True)
    counterparty_uuid = Column(String(length=36), nullable=True)
    # ... если есть указание Заявки, то она относится именно к ней
    application_id = Column(BigInteger, ForeignKey("application.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=True)
    application_uuid = Column(String(length=36), nullable=True)
    
    # Эта директория будет относится к карточке КП
    directory_id = Column(BigInteger, ForeignKey("directory.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    directory_uuid = Column(String(length=36), nullable=False)
    
    # Сам документ КП
    document_uuid = Column(String(length=36), nullable=True)
    
    status = Column(SmallInteger, ForeignKey("application_status.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    
    can_be_updated_by_user = Column(Boolean, server_default="true")  # Аналогичное поле как у Заявки/карточки-Контрагента
    
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
