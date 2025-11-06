from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text

from connection_module import Base


class MTApplicationData(Base):
    __tablename__ = "mt_application_data"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    order_name = Column(String, nullable=True)
    
    payment_deadline_not_earlier_than = Column(Date)
    payment_deadline_no_later_than = Column(Date)
    invoice_date = Column(Date)
    
    type = Column(SmallInteger, ForeignKey("mt_application_type.id", ondelete="CASCADE", onupdate="CASCADE"))
    
    invoice_currency = Column(SmallInteger, ForeignKey("currency.id", ondelete="CASCADE", onupdate="CASCADE"), comment="Валюта счета")
    invoice_amount = Column(Numeric, comment="Сумма счета")
    payment_amount = Column(Numeric, comment="Сумма платежа, если она отличается от суммы счета")
    payment_amount_in_words = Column(String, comment="Сумма платежа прописью на английском языке")
    partial_payment_allowed = Column(Boolean, comment="Возможна ли частичная оплата?")
    invoice_number = Column(String, comment="Номер счета на оплату")
    
    amount_to_withdraw = Column(Numeric, comment="Сумма, подлежащая снятию с депозитного счета")
    amount_to_replenish = Column(Numeric, comment="Сумма для пополнения депозита")
    amount_to_principal = Column(Numeric, comment="Сумма перечисления Принципалу")
    amount_credited = Column(Numeric, comment="Сумма зачисления")
    is_amount_different = Column(Boolean, comment="Может ли итоговая сумма поступления на счет Субагента отличаться от суммы платежа?")
    source_bank = Column(String, comment="Со счета в каком банке необходимо осуществить перевод денежных средств?")
    target_bank = Column(String, comment="На счет в каком банке необходимо зачислить денежные средства?")
    source_currency = Column(SmallInteger, ForeignKey("currency.id", ondelete="CASCADE", onupdate="CASCADE"), comment="Исходная валюта")
    target_currency = Column(SmallInteger, ForeignKey("currency.id", ondelete="CASCADE", onupdate="CASCADE"), comment="Целевая валюта")
    amount = Column(Numeric, comment="Сумма")
    subagent_bank = Column(String, comment="Банк Субагента")
    
    payment_purpose_ru = Column(String, comment="Назначение платежа на русском языке (для переводов в России)")
    payment_purpose_en = Column(String, comment="Назначение платежа на английском языке (для переводов за пределами России). Ограничения: Golomt Bank - 50 символов, Khan Bank - 90 символов. Исключить аббревиатуру <RUS>. Не упоминать контракт. Указать данные счета и за какие услуги/товары производится оплата.")
    payment_category_golomt = Column(String, comment="Категории платежа на латинице для Golomt Bank (выбрать из списка)")
    payment_category_td = Column(String, comment="Категории платежа на латинице для TD Bank (выбрать из списка)")
    goods_description_en = Column(String, comment="Наименования товаров на английском языке (если платеж осуществляется за товары)")
    
    contract_date = Column(Date, comment="Дата подписания договора с получателем платежа")
    contract_name = Column(String, comment="Наименование договора")
    contract_number = Column(String, comment="Номер договора с получателем платежа")
    vat_exempt = Column(Boolean, comment="НДС не облагается")
    vat_percentage = Column(Numeric, comment="% НДС")
    vat_amount = Column(Numeric, comment="Сумма НДС")
    priority = Column(String, comment="Приоритет")
    
    end_customer_company_name = Column(String, comment="Наименование компании конечного покупателя")
    end_customer_company_legal_form = Column(String, comment="Организационно-правовая форма компании конечного покупателя")
    end_customer_company_registration_country = Column(SmallInteger, ForeignKey("country.id", ondelete="CASCADE", onupdate="CASCADE"), comment="Страна регистрации компании конечного покупателя")
    
    company_name_latin = Column(String, comment="Наименование компании в латинском написании")
    company_name_national = Column(String, comment="Наименование компании в национальном написании")
    company_legal_form = Column(String, comment="Организационно-правовая форма компании - получателя платежа")
    company_address_latin = Column(String, comment="Адрес компании - получателя платежа - в латинском написании")
    company_registration_number = Column(String, comment="Регистрационный номер (ОГРН) компании - получателя платежа")
    company_tax_number = Column(String, comment="Налоговый номер (ИНН) компании - получателя платежа")
    company_internal_identifier = Column(String, comment="Внутренний идентификационный номер компании - получателя платежа")
    recipient_first_name = Column(String, comment="Имя получателя платежа (если перевод осуществляется частному лицу)")
    recipient_last_name = Column(String, comment="Фамилия получателя платежа (если перевод осуществляется частному лицу)")
    recipient_id_number = Column(String, comment="Идентификационный номер получателя платежа (если перевод осуществляется частному лицу)")
    recipient_phone = Column(String, comment="Телефон получателя платежа")
    recipient_website = Column(String, comment="Веб-сайт получателя платежа")
    transaction_confirmation_type = Column(String, comment="Какой вид подтверждения банковской сделки необходим?")
    
    recipient_bank_name_latin = Column(String, comment="Наименование банка получателя платежа в латинском написании")
    recipient_bank_name_national = Column(String, comment="Наименование банка получателя платежа в национальном написании")
    recipient_bank_legal_form = Column(String, comment="Организационно-правовая форма банка получателя платежа")
    recipient_bank_registration_number = Column(String, comment="Регистрационный номер банка получателя платежа")
    recipient_account_or_iban = Column(String, comment="Расчетный счет получателя или IBAN")
    recipient_swift = Column(String, comment="SWIFT")
    recipient_bic = Column(String, comment="БИК")
    recipient_bank_code = Column(String, comment="Банковский код получателя")
    recipient_bank_branch = Column(String, comment="Отделение банка")
    spfs = Column(String, comment="Система передачи финансовых сообщений (СПФС)")
    cips = Column(String, comment="CIPS (Система трансграничных межбанковских платежей в китайских юанях (RMB))")
    recipient_bank_address = Column(String, comment="Адрес банка получателя")
    
    sender_company_name_latin = Column(String, comment="Наименование компании - отправителя платежа в латинском написании")
    sender_company_name_national = Column(String, comment="Наименование компании - отправителя платежа в национальном написании")
    sender_company_legal_form = Column(String, comment="Организационно-правовая форма компании - отправителя платежа")
    sender_country = Column(SmallInteger, ForeignKey("country.id", ondelete="CASCADE", onupdate="CASCADE"), comment="Страна отправителя платежа")
    
    comment = Column(Text)
    
    updated_at = Column(DateTime(timezone=True))

class MTApplicationType(Base):
    __tablename__ = "mt_application_type"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    
    name = Column(String)
    description = Column(Text)
