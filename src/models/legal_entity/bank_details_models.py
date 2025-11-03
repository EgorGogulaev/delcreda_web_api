from sqlalchemy import (
    Boolean, Column, Integer, func, ForeignKey, Index,
    BigInteger,
    String,
    DateTime,
)

from connection_module import Base


class BankDetails(Base):
    __tablename__ = "bank_detail"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    user_uuid = Column(String(length=36), nullable=False)
    legal_entity_uuid = Column(String(length=36))  # Поле должно быть НЕ нулевым, если from_customer == True
    
    name_latin = Column(String)
    name_national = Column(String)
    
    organizational_and_legal_form = Column(String)
    
    SWIFT = Column(String)
    BIC = Column(String)
    IBAN = Column(String)
    
    banking_messaging_system = Column(String)
    CIPS = Column(String)
    
    registration_identifier = Column(String)
    
    current_account_rub = Column(String)
    current_account_eur = Column(String)
    current_account_usd = Column(String)
    current_account_cny = Column(String)
    current_account_chf = Column(String)
    correspondence_account = Column(String)
    
    address = Column(String)
    
    updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)
