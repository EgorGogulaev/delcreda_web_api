from sqlalchemy import (
    Boolean, Column, Date, Integer, SmallInteger, UniqueConstraint, func, ForeignKey, Index,
    BigInteger,
    String,
    DateTime,
)

from connection_module import Base


class LegalEntity(Base):
    __tablename__ = "legal_entity"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(String(length=36), unique=True, nullable=False)
    
    country = Column(SmallInteger, ForeignKey("country.id", ondelete="NO ACTION", onupdate="CASCADE"), nullable=False)
    registration_identifier_type = Column(String)
    registration_identifier_value = Column(String, nullable=False)
    tax_identifier = Column(String, nullable=False)
    
    user_id = Column(Integer, ForeignKey("user_account.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    user_uuid = Column(String(length=36), nullable=False)
    directory_id = Column(BigInteger, ForeignKey("directory.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    directory_uuid = Column(String(length=36), nullable=False)
    is_active = Column(Boolean, server_default="false", nullable=False)
    
    data_id = Column(BigInteger, ForeignKey("legal_entity_data.id", ondelete="CASCADE", onupdate="CASCADE"))
    can_be_updated_by_user = Column(Boolean, server_default="true")
    
    order_access_list = Column(BigInteger, ForeignKey("order_access_list.id", ondelete="CASCADE", onupdate="CASCADE"))
    
    updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)
    
    __table_args__ = (
        UniqueConstraint(
            'country', 'registration_identifier_type', 'registration_identifier_value', 
            name='uq_country_reg_type_reg_value'
        ),
    )

class LegalEntityData(Base):
    __tablename__ = "legal_entity_data"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Регистрационные данные
    name_latin = Column(String)
    name_national = Column(String)
    
    organizational_and_legal_form_latin = Column(String)
    organizational_and_legal_form_national = Column(String)
    
    site = Column(String)
    registration_date = Column(Date)
    
    legal_address = Column(String)
    postal_address = Column(String)
    additional_address = Column(String)
    
    updated_at = Column(DateTime(timezone=True))

class OrderAccessList(Base):
    __tablename__ = "order_access_list"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    mt = Column(Boolean, server_default="false", nullable=False)  # перевод денежных средств
    # TODO Реализовать список услуг

class Person(Base):
    __tablename__ = "person"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    surname = Column(String)
    name = Column(String)
    patronymic = Column(String)
    gender = Column(String)
    
    job_title = Column(String)
    basic_action_signatory = Column(String, nullable=True)  # Устав/Доверенность/Иное
    
    power_of_attorney_number = Column(String, nullable=True,)  # Если доверенность
    power_of_attorney_date = Column(Date, nullable=True,)  # Если доверенность
    
    email = Column(String)
    phone = Column(String)
    contact = Column(String)
    
    legal_entity_uuid = Column(String(length=36), nullable=False)
    
    updated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)
