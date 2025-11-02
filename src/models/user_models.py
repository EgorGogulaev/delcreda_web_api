from sqlalchemy import (
    BigInteger, Column, Integer, func, ForeignKey, Index,
    SmallInteger,
    String, Text,
    Boolean,
    DateTime
)

from connection_module import Base


class Token(Base):
    __tablename__ = "token"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    value = Column(String(length=36), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)

class UserAccount(Base):
    __tablename__ = "user_account"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(length=36), nullable=False, unique=True)
    token = Column(Integer, ForeignKey("token.id", ondelete="NO ACTION", onupdate="CASCADE"))
    
    login = Column(String(length=255), unique=True, nullable=False)
    password = Column(String(length=255), nullable=False)
    privilege = Column(SmallInteger, ForeignKey("user_privilege.id", onupdate="CASCADE", ondelete="NO ACTION"), nullable=False)
    is_active = Column(Boolean, server_default="true", nullable=False)
    contact = Column(BigInteger, ForeignKey("user_contact.id", ondelete="NO ACTION", onupdate="CASCADE"))
    
    s3_login = Column(String(length=64), nullable=False)
    s3_password = Column(String(length=64), nullable=False)
    
    last_auth = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.timezone('UTC', func.current_timestamp()), nullable=False)
    
    __table_args__ = (
        Index("idx_user_account_login", login),
        Index("idx_user_account_uuid", uuid)
    ,)
    
    def _to_list(self):
        return [
            self.id,
            self.uuid,
            self.token,
            self.login,
            self.password,
            self.privilege,
            self.is_active,
            self.last_auth,
            self.created_at,
        ]

class UserPrivilege(Base):
    __tablename__ = "user_privilege"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String(length=50))
    description = Column(Text)

class UserContact(Base):
    __tablename__ = "user_contact"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    email = Column(String, unique=True, nullable=True)
    email_notification = Column(Boolean, server_default="false", nullable=False)
    
    telegram = Column(String, unique=True, nullable=True)
    telegram_notification = Column(Boolean, server_default="false", nullable=False)
