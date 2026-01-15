from sqlalchemy import (
    Column, Integer, SmallInteger, func, ForeignKey, Index,
    BigInteger,
    String, Text,
    Date, DateTime,
)

from connection_module import Base


class Contract(Base):
    __tablename__ = "contract"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    uuid = Column(String(length=36), unique=True, nullable=False)
    
    name = Column(String, nullable=True)  # Название берется из прикрепленного Документа
    type = Column(SmallInteger, ForeignKey("contract_type.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    
    # Пользователь к кому относится КП
    user_id = Column(Integer, ForeignKey("user_account.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    user_uuid = Column(String(length=36), nullable=False)
    
    # к чему привязка? Если только к Контрагенту - Договор "верхнеуровневый"...
    counterparty_id = Column(Integer, ForeignKey("counterparty.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=True)
    counterparty_uuid = Column(String(length=36), nullable=True)
    # ... если есть указание Заявки, то Договор относится именно к ней
    application_id = Column(BigInteger, ForeignKey("application.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=True)
    application_uuid = Column(String(length=36), nullable=True)
    
    document_uuid = Column(String(length=36))
    
    start_date = Column(Date)
    expiration_date = Column(Date)
    
    updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)

class ContractType(Base):
    __tablename__ = "contract_type"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
    description = Column(Text)
