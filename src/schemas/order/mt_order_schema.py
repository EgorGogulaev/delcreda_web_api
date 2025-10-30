from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from src.schemas.order.order_schema import BaseOrder
from src.utils.reference_mapping_data.order.order.mt_mapping import MT_ORDER_TYPE_MAPPING
from src.schemas.reference_schema import CountryKey
from src.utils.reference_mapping_data.app.app_mapping_data import COUNTRY_MAPPING


MTOrderTypeKey: type = Literal[*MT_ORDER_TYPE_MAPPING]


class CreateMTOrderDataSchema(BaseModel):
    payment_deadline_not_earlier_than: Optional[str]
    payment_deadline_no_later_than: Optional[str]
    invoice_date: Optional[str] = None
    
    type: MTOrderTypeKey  # type: ignore  Тип поручения
    
    invoice_currency: Optional[str] = None  # Валюта счета
    invoice_amount: Optional[str] = None  # Сумма счета
    payment_amount: Optional[str] = None  # Сумма платежа, если она отличается от суммы счета
    payment_amount_in_words: Optional[str] = None  # Сумма платежа прописью на английском языке
    partial_payment_allowed: Optional[bool] = None  # Возможна ли частичная оплата?
    invoice_number: Optional[str] = None  # Номер/а счета/ов на оплату
    
    amount_to_withdraw: Optional[str] = None  # Сумма, подлежащая снятию с депозитного счета
    amount_to_replenish: Optional[str] = None  # Сумма для пополнения депозита
    amount_to_principal: Optional[str] = None  # Сумма перечисления Принципалу
    amount_credited: Optional[str] = None  # Сумма зачисления
    is_amount_different: Optional[bool] = None  # Может ли итоговая сумма поступления на счет Субагента отличаться от суммы платежа?
    source_bank: Optional[str] = None  # Со счета в каком банке необходимо осуществить перевод денежных средств?
    target_bank: Optional[str] = None  # На счет в каком банке необходимо зачислить денежные средства?
    source_currency: Optional[str] = None  # Исходная валюта
    target_currency: Optional[str] = None  # Целевая валюта
    amount: Optional[str] = None  # Сумма
    subagent_bank: Optional[str] = None  # Банк Субагента
    
    payment_purpose_ru: Optional[str] = None  # Назначение платежа на русском языке (для переводов в России)
    payment_purpose_en: Optional[str] = None  # Назначение платежа на английском языке (для переводов за пределами России). Ограничения: Golomt Bank - 50 символов, Khan Bank - 90 символов. Исключить аббревиатуру <RUS>. Не упоминать контракт. Указать данные счета и за какие услуги/товары производится оплата.
    payment_category_golomt: Optional[str] = None  # Категории платежа на латинице для Golomt Bank (выбрать из списка)
    payment_category_td: Optional[str] = None  # Категории платежа на латинице для TD Bank (выбрать из списка)
    goods_description_en: Optional[str] = None  # Наименования товаров на английском языке (если платеж осуществляется за товары)
    
    contract_date: Optional[str] = None  # Дата подписания договора с получателем платежа
    contract_name: Optional[str] = None  # Наименование договора
    contract_number: Optional[str] = None  # Номер договора с получателем платежа
    vat_exempt: Optional[str] = None  # НДС не облагается
    vat_percentage: Optional[str] = None  # % НДС
    vat_amount: Optional[str] = None  # Сумма НДС
    priority: Optional[str] = None  # Приоритет
    
    end_customer_company_name: Optional[str] = None  # Наименование компании конечного покупателя
    end_customer_company_legal_form: Optional[str] = None  # Организационно-правовая форма компании конечного покупателя
    end_customer_company_registration_country: Optional[CountryKey] = None # type: ignore Страна регистрации компании конечного покупателя
    
    company_name_latin: Optional[str] = None  # Наименование компании в латинском написании
    company_name_national: Optional[str] = None  # Наименование компании в национальном написании
    company_legal_form: Optional[str] = None  # Организационно-правовая форма компании - получателя платежа
    company_address_latin: Optional[str] = None  # Адрес компании - получателя платежа - в латинском написании
    company_registration_number: Optional[str] = None  # Регистрационный номер (ОГРН) компании - получателя платежа
    company_tax_number: Optional[str] = None  # Налоговый номер (ИНН) компании - получателя платежа
    company_internal_identifier: Optional[str] = None  # Внутренний идентификационный номер компании - получателя платежа
    recipient_first_name: Optional[str] = None  # Имя получателя платежа (если перевод осуществляется частному лицу)
    recipient_last_name: Optional[str] = None  # Фамилия получателя платежа (если перевод осуществляется частному лицу)
    recipient_id_number: Optional[str] = None  # Идентификационный номер получателя платежа (если перевод осуществляется частному лицу)
    recipient_phone: Optional[str] = None  # Телефон получателя платежа
    recipient_website: Optional[str] = None  # Веб-сайт получателя платежа
    transaction_confirmation_type: Optional[str] = None  # Какой вид подтверждения банковской сделки необходим?
    
    recipient_bank_name_latin: Optional[str] = None  # Наименование банка получателя платежа в латинском написании
    recipient_bank_name_national: Optional[str] = None  # Наименование банка получателя платежа в национальном написании
    recipient_bank_legal_form: Optional[str] = None  # Организационно-правовая форма банка получателя платежа
    recipient_bank_registration_number: Optional[str] = None  # Регистрационный номер банка получателя платежа
    recipient_account_or_iban: Optional[str] = None  # Расчетный счет получателя или IBAN
    recipient_swift: Optional[str] = None  # SWIFT
    recipient_bic: Optional[str] = None  # БИК
    recipient_bank_code: Optional[str] = None  # Банковский код получателя
    recipient_bank_branch: Optional[str] = None  # Отделение банка
    spfs: Optional[str] = None  # Система передачи финансовых сообщений (СПФС)
    cips: Optional[str] = None  # CIPS (Система трансграничных межбанковских платежей в китайских юанях (RMB))
    recipient_bank_address: Optional[str] = None  # Адрес банка получателя
    
    sender_company_name_latin: Optional[str] = None  # Наименование компании - отправителя платежа в латинском написании
    sender_company_name_national: Optional[str] = None  # Наименование компании - отправителя платежа в национальном написании
    sender_company_legal_form: Optional[str] = None  # Организационно-правовая форма компании - отправителя платежа
    sender_country: Optional[CountryKey] = None # type: ignore  Страна отправителя платежа
    
    comment: Optional[str] = None  # Комментарий к Поручению
"""
поля НЕ используемы для предзаполнения:

payment_deadline_not_earlier_than
payment_deadline_no_later_than
payment_amount
payment_amount_in_words
amount_to_withdraw
amount_to_replenish
amount_to_principal
amount_credited
vat_amount
"""
class UpdateMTOrderDataSchema(BaseModel):
    payment_deadline_not_earlier_than: Optional[str] = "~"                # 1.1, 1.2, 1.3, 1.4,  - , 2.1,  - ,  - ,  -            # Срок оплаты не раньше V
    payment_deadline_no_later_than: Optional[str] = "~"                   # 1.1, 1.2, 1.3, 1.4,  - , 2.1,  - ,  - ,  -            # Срок оплаты не позже V
    invoice_date: Optional[str] = "~"                                     # 1.1, 1.2, 1.3, 1.4,  - , 2.1,  - ,  - ,  -            # Дата cчёта на оплату V
    
    invoice_currency: Optional[str] = "~"                                 # 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 3.1,  -            # Валюта счета V
    invoice_amount: Optional[str] = "~"                                   # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Сумма счета V
    payment_amount: Optional[str] = "~"                                   # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Сумма платежа, если она отличается от суммы счета V
    payment_amount_in_words: Optional[str] = "~"                          # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Сумма платежа прописью на английском языке V
    partial_payment_allowed: Optional[bool|str] = "~"                     # 1.1,  - , 1.3, 1.4,  - , 2.1,  - ,  - ,  -            # Возможна ли частичная оплата? V
    invoice_number: Optional[str] = "~"                                   # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Номер счета на оплату V
    
    amount_to_withdraw: Optional[str] = "~"                               #  - ,  - , 1.3, 1.4,  - ,  - ,  - ,  - ,  -            # Сумма, подлежащая снятию с депозитного счета V
    amount_to_replenish: Optional[str] = "~"                              #  - ,  - , 1.3,  -    - ,  - ,  - ,  - ,  -            # Сумма для пополнения депозита V
    amount_to_principal: Optional[str] = "~"                              #  - ,  - ,  - , 1.4,  - ,  - ,  - ,  - ,  -            # Сумма перечисления Принципалу V
    amount_credited: Optional[str] = "~"                                  #  - ,  - ,  - ,  - , 1.5,  - , 2.2,  - ,  -            # Сумма зачисления V
    is_amount_different: Optional[bool|str] = "~"                         #  - , 1.2,  - , 1.4, 1.5,  - , 2.2,  - ,  -            # Может ли итоговая сумма поступления на счет Субагента отличаться от суммы платежа? V
    source_bank: Optional[str] = "~"                                      #  - ,  - ,  - ,  - ,  - ,  - ,  - , 3.1,  -            # Со счета в каком банке необходимо осуществить перевод денежных средств? V
    target_bank: Optional[str] = "~"                                      #  - ,  - ,  - ,  - ,  - ,  - ,  - , 3.1,  -            # На счет в каком банке необходимо зачислить денежные средства? V
    source_currency: Optional[str] = "~"                                  #  - ,  - ,  - ,  - ,  - ,  - ,  - , 3.1, 3.2           # Исходная валюта V
    target_currency: Optional[str] = "~"                                  #  - ,  - ,  - ,  - ,  - ,  - ,  - , 3.1, 3.2           # Целевая валюта V
    amount: Optional[str] = "~"                                           #  - ,  - ,  - ,  - ,  - ,  - ,  - , 3.1, 3.2           # Сумма V
    subagent_bank: Optional[str] = "~"                                    #  - ,  - ,  - ,  - ,  - ,  - ,  - , 3.1,о3.2           # Банк Субагента V
    
    payment_purpose_ru: Optional[str] = "~"                               # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Назначение платежа на русском языке (для переводов в России) V
    payment_purpose_en: Optional[str] = "~"                               # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Назначение платежа на английском языке (для переводов за пределами России). Ограничения: Golomt Bank - 50 символов, Khan Bank - 90 символов. Исключить аббревиатуру <RUS>. Не упоминать контракт. Указать данные счета и за какие услуги/товары производится оплата. V
    payment_category_golomt: Optional[str] = "~"                          # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Категории платежа на латинице для Golomt Bank (выбрать из списка) V
    payment_category_td: Optional[str] = "~"                              # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Категории платежа на латинице для TD Bank (выбрать из списка) V
    goods_description_en: Optional[str] = "~"                             # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Наименования товаров на английском языке (если платеж осуществляется за товары) V
    
    contract_date: Optional[str] = "~"                                    # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Дата подписания договора с получателем платежа V
    contract_name: Optional[str] = "~"                                    # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Наименование договора V
    contract_number: Optional[str] = "~"                                  # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Номер договора с получателем платежа V
    vat_exempt: Optional[str] = "~"                                       # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # НДС не облагается V
    vat_percentage: Optional[str] = "~"                                   # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # % НДС V
    vat_amount: Optional[str] = "~"                                       # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Сумма НДС V
    priority: Optional[str] = "~"                                         # 1.1, 1.2, 1.3, 1.4,  - , 2.1, 2.2,  - ,  -            # Приоритет V
    
    end_customer_company_name: Optional[str] = "~"                        #о1.1,  - ,о1.3,  - ,  - ,о2.1,  - ,  - ,  -            # Наименование компании конечного покупателя
    end_customer_company_legal_form: Optional[str] = "~"                  #о1.1,  - ,о1.3,  - ,  - ,о2.1,  - ,  - ,  -            # Организационно-правовая форма компании конечного покупателя
    end_customer_company_registration_country: Literal[
        *COUNTRY_MAPPING, "~" # type: ignore
    ] = "~"                                                               #о1.1,  - ,о1.3,  - ,  - ,о2.1,  - ,  - ,  -            # Страна регистрации компании конечного покупателя
    
    company_name_latin: Optional[str] = "~"                               # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Наименование компании в латинском написании V
    company_name_national: Optional[str] = "~"                            # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Наименование компании в национальном написании V
    company_legal_form: Optional[str] = "~"                               # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Организационно-правовая форма компании - получателя платежа V
    company_address_latin: Optional[str] = "~"                            # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Адрес компании - получателя платежа - в латинском написании V
    company_registration_number: Optional[str] = "~"                      # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Регистрационный номер (ОГРН) компании - получателя платежа V
    company_tax_number: Optional[str] = "~"                               # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Налоговый номер (ИНН) компании - получателя платежа V
    company_internal_identifier: Optional[str] = "~"                      #о1.1,  - ,о1.3,  - ,  - ,о2.1,  - ,  - ,  -            # Внутренний идентификационный номер компании - получателя платежа V
    recipient_first_name: Optional[str] = "~"                             #о1.1,  - ,о1.3,  - ,  - ,о2.1,  - ,  - ,  -            # Имя получателя платежа (если перевод осуществляется частному лицу) V
    recipient_last_name: Optional[str] = "~"                              #о1.1,  - ,о1.3,  - ,  - ,о2.1,  - ,  - ,  -            # Фамилия получателя платежа (если перевод осуществляется частному лицу) V
    recipient_id_number: Optional[str] = "~"                              #о1.1,  - ,о1.3,  - ,  - ,о2.1,  - ,  - ,  -            # Идентификационный номер получателя платежа (если перевод осуществляется частному лицу) V
    recipient_phone: Optional[str] = "~"                                  # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Телефон получателя платежа V
    recipient_website: Optional[str] = "~"                                # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Веб-сайт получателя платежа V
    transaction_confirmation_type: Optional[str] = "~"                    # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Какой вид подтверждения банковской сделки необходим? V
    
    recipient_bank_name_latin: Optional[str] = "~"                        # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Наименование банка получателя платежа в латинском написании V
    recipient_bank_name_national: Optional[str] = "~"                     # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Наименование банка получателя платежа в национальном написании V
    recipient_bank_legal_form: Optional[str] = "~"                        # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Организационно-правовая форма банка получателя платежа V
    recipient_bank_registration_number: Optional[str] = "~"               # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Регистрационный номер банка получателя платежа V
    recipient_account_or_iban: Optional[str] = "~"                        # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Расчетный счет получателя или IBAN V
    recipient_swift: Optional[str] = "~"                                  # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # SWIFT V
    recipient_bic: Optional[str] = "~"                                    # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # БИК V
    recipient_bank_code: Optional[str] = "~"                              # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Банковский код получателя V
    recipient_bank_branch: Optional[str] = "~"                            # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Отделение банка V
    spfs: Optional[str] = "~"                                             #о1.1,  - ,о1.3,  - ,  - ,о2.1,  - ,  - ,  -            # Система передачи финансовых сообщений (СПФС) V
    cips: Optional[str] = "~"                                             #о1.1,  - ,о1.3,  - ,  - ,о2.1,  - ,  - ,  -            # CIPS (Система трансграничных межбанковских платежей в китайских юанях (RMB)) V
    recipient_bank_address: Optional[str] = "~"                           # 1.1,  - , 1.3,  - ,  - , 2.1,  - ,  - ,  -            # Адрес банка получателя V
    
    sender_company_name_latin: Optional[str] = "~"                        #  - , 1.2,  - , 1.4,  - ,  - , 2.2,  - ,  -            # Наименование компании - отправителя платежа в латинском написании V
    sender_company_name_national: Optional[str] = "~"                     #  - , 1.2,  - , 1.4,  - ,  - , 2.2,  - ,  -            # Наименование компании - отправителя платежа в национальном написании V
    sender_company_legal_form: Optional[str] = "~"                        #  - , 1.2,  - , 1.4,  - ,  - , 2.2,  - ,  -            # Организационно-правовая форма компании - отправителя платежа V
    sender_country: Literal[*COUNTRY_MAPPING, "~"] = "~" # type: ignore      - , 1.2,  - , 1.4,  - ,  - , 2.2,  - ,  -              Страна отправителя платежа V
    
    comment: Optional[str] = "~"                                          # 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 3.1, 3.2           # Особенности проведения поручения V


class ExtendedMTOrder(BaseOrder):
    type: Optional[str] = Field(None, description="Тип поручения по MT.")
    priority: Optional[str] = Field(None, description="Приоритет поручения.")
    user_login: Optional[str] = Field(None, description="Логин Пользователя, который создал ПР.")
    legal_entity_name_latin: Optional[str] = Field(None, description="Наименование ЮЛ от которого создан ПР (латиница).")
    legal_entity_name_national: Optional[str] = Field(None, description="Наименование ЮЛ от которого создан ПР (национальное написание).")
    data_updated_at: Optional[str] = Field(None, description="Дата-время последнего обновления данных ПР (Формат: 'dd.mm.YYYY HH:MM:SS TZ').")

class ResponseGetMTOrders(BaseModel):
    data: List[Optional[Union[BaseOrder, ExtendedMTOrder]]] = Field([], description="Массив Поручений по MT.")
    count: int = Field(0, description="Количество записей по текущей фильтрации (с учетом пагинации).")
    total_records: Optional[int] = Field(None, description="Всего записей (нужно для реализации пагинации в таблице).")
    total_pages: Optional[int] = Field(None, description="Всего страниц, с текущим размером страницы(page_size).")
