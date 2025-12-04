from typing import List, Optional
from pydantic import BaseModel, Field


class CreateBankDetailsSchema(BaseModel):
    user_uuid: str = Field(..., description="UUID пользователя, к которому относятся банковские реквизиты.")
    counterparty_uuid: Optional[str] = Field(None, description="UUID Контрагента к которому будут прикреплены данные банковских реквизитов.")
    name_latin: Optional[str] = Field(None, description="Наименование банка латиницей.")
    name_national: Optional[str] = Field(None, description="Наименование банка в национальном написании.")
    organizational_and_legal_form: Optional[str] = Field(None, description="ОПФ.")
    SWIFT: Optional[str] = Field(None, description="SWIFT.")
    BIC: Optional[str] = Field(None, description="BIC.")
    IBAN: Optional[str] = Field(None, description="IBAN.")
    banking_messaging_system: Optional[str] = Field(None, description="Система банковских сообщений.")
    CIPS: Optional[str] = Field(None, description="CIPS.")
    registration_identifier: Optional[str] = Field(None, description="Регистрационный идентификатор.")
    current_account_rub: Optional[str] = Field(None, description="Счет в рублях.")
    current_account_eur: Optional[str] = Field(None, description="Счет в евро.")
    current_account_usd: Optional[str] = Field(None, description="Счет в долларах США.")
    current_account_cny: Optional[str] = Field(None, description="Счет в юанях.")
    current_account_chf: Optional[str] = Field(None, description="Счет в швейцарских франках.")
    correspondence_account: Optional[str] = Field(None, description="Корреспондентский счет")
    address: Optional[str] = Field(None, description="Адрес банка.")

class CreateBanksDetailsSchema(BaseModel):
    new_banks_details: List[CreateBankDetailsSchema] = Field(..., description="Массив банковских реквизитов.")

class UpdateBankDetailsSchema(BaseModel):
    user_uuid: Optional[str] = Field("~", description="UUID пользователя, к которому относятся банковские реквизиты. (значение '~' == оставить без изменений)")
    counterparty_uuid: Optional[str] = Field("~", description="UUID Контрагента к которому будут прикреплены данные банковских реквизитов. (значение '~' == оставить без изменений)")
    name_latin: Optional[str] = Field("~", description="Наименование банка латиницей. (значение '~' == оставить без изменений)")
    name_national: Optional[str] = Field("~", description="Наименование банка в национальном написании. (значение '~' == оставить без изменений)")
    organizational_and_legal_form: Optional[str] = Field("~", description="ОПФ. (значение '~' == оставить без изменений)")
    SWIFT: Optional[str] = Field("~", description="SWIFT. (значение '~' == оставить без изменений)")
    BIC: Optional[str] = Field("~", description="BIC. (значение '~' == оставить без изменений)")
    IBAN: Optional[str] = Field("~", description="IBAN. (значение '~' == оставить без изменений)")
    banking_messaging_system: Optional[str] = Field("~", description="Система банковских сообщений. (значение '~' == оставить без изменений)")
    CIPS: Optional[str] = Field("~", description="CIPS. (значение '~' == оставить без изменений)")
    registration_identifier: Optional[str] = Field("~", description="Регистрационный идентификатор. (значение '~' == оставить без изменений)")
    current_account_rub: Optional[str] = Field("~", description="Счет в рублях. (значение '~' == оставить без изменений)")
    current_account_eur: Optional[str] = Field("~", description="Счет в евро. (значение '~' == оставить без изменений)")
    current_account_usd: Optional[str] = Field("~", description="Счет в долларах США. (значение '~' == оставить без изменений)")
    current_account_cny: Optional[str] = Field("~", description="Счет в юанях. (значение '~' == оставить без изменений)")
    current_account_chf: Optional[str] = Field("~", description="Счет в швейцарских франках. (значение '~' == оставить без изменений)")
    correspondence_account: Optional[str] = Field("~", description="Корреспондентский счет (значение '~' == оставить без изменений)")
    address: Optional[str] = Field("~", description="Адрес банка. (значение '~' == оставить без изменений)")
