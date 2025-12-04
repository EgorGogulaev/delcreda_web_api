from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.counterparty.bank_details_models import BankDetails
from src.query_and_statement.counterparty.bank_details_qas_manager import BankDetailsQueryAndStatementManager
from src.query_and_statement.counterparty.counterparty_qas_manager import CounterpartyQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.schemas.counterparty.bank_details_schema import CreateBanksDetailsSchema


class BankDetailsService:
    @staticmethod
    async def create_banks_details(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        new_banks_details: CreateBanksDetailsSchema,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            counterparty_uuid_tuple = tuple(set([new_bank_details.counterparty_uuid for new_bank_details in new_banks_details.new_banks_details]))
            if len(counterparty_uuid_tuple) != 1:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете добавлять реквизиты к карточкам Контрагента других Пользователей!")
            
            counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                counterparty_uuid=counterparty_uuid_tuple[0],
            )
            if counterparty_check_access_response_object is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете добавлять реквизиты к карточкам Контрагента других Пользователей!")
        
        await BankDetailsQueryAndStatementManager.create_banks_details(
            session=session,
            new_banks_details=new_banks_details,
        )
    
    @staticmethod
    async def get_banks_details(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        counterparty_uuid: Optional[str] = None,
        user_uuid: Optional[str] = None,
    ) -> List[Optional[BankDetails]]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not counterparty_uuid and not user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Реквизиты других Пользователей!")
            if user_uuid:
                if requester_user_uuid != user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Реквизиты других Пользователей!")
            if counterparty_uuid:
                counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    counterparty_uuid=counterparty_uuid,
                )
                if counterparty_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть информацию о Реквизитах в карточках Контрагента других Пользователей!")
        
        banks_details: List[Optional[BankDetails]] = await BankDetailsQueryAndStatementManager.get_banks_details(
            session=session,
            
            counterparty_uuid=counterparty_uuid,
            user_uuid=user_uuid,
        )
        
        return banks_details
    
    @staticmethod
    async def update_bank_details(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        bank_details_id: int,
        user_uuid: Optional[str],
        counterparty_uuid: Optional[str],
        name_latin: Optional[str],
        name_national: Optional[str],
        organizational_and_legal_form: Optional[str],
        SWIFT: Optional[str],
        BIC: Optional[str],
        IBAN: Optional[str],
        banking_messaging_system: Optional[str],
        CIPS: Optional[str],
        registration_identifier: Optional[str],
        current_account_rub: Optional[str],
        current_account_eur: Optional[str],
        current_account_usd: Optional[str],
        current_account_cny: Optional[str],
        current_account_chf: Optional[str],
        correspondence_account: Optional[str],
        address: Optional[str],
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            bank_details: List[Optional[BankDetails]] = await BankDetailsQueryAndStatementManager.get_banks_details(
                session=session,
                bank_details_ids=[bank_details_id]
            )
            if not bank_details:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись о Реквизитах не была найдена по ID!")
            if bank_details[0].user_uuid != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете обновить запись о Реквизитах другого Пользователя!")
            if bank_details[0].counterparty_uuid:
                counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    counterparty_uuid=bank_details[0].counterparty_uuid,
                )
                if counterparty_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете обновить информацию о Реквизитах в карточках Контрагента других Пользователей!")
        
        if all(field == "~" for field in [
                user_uuid, counterparty_uuid,
                name_latin, name_national,
                organizational_and_legal_form,
                SWIFT, BIC, IBAN, banking_messaging_system, CIPS,
                registration_identifier,
                current_account_rub, current_account_eur, current_account_usd, current_account_cny, current_account_chf, correspondence_account,
                address,
            ]
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Хотя бы одно поле должно быть изменено для обновления данных о Реквизитах!")
        
        await BankDetailsQueryAndStatementManager.update_bank_details(
            session=session,
            
            bank_details_id=bank_details_id,
            
            user_uuid=user_uuid,
            counterparty_uuid=counterparty_uuid,
            name_latin=name_latin,
            name_national=name_national,
            organizational_and_legal_form=organizational_and_legal_form,
            SWIFT=SWIFT,
            BIC=BIC,
            IBAN=IBAN,
            banking_messaging_system=banking_messaging_system,
            CIPS=CIPS,
            registration_identifier=registration_identifier,
            current_account_rub=current_account_rub,
            current_account_eur=current_account_eur,
            current_account_usd=current_account_usd,
            current_account_cny=current_account_cny,
            current_account_chf=current_account_chf,
            correspondence_account=correspondence_account,
            address=address,
        )
    
    @staticmethod
    async def delete_banks_details(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        bank_details_ids: List[int],
    ) -> None:
        if not bank_details_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Должен быть указан хотя бы 1 ID банковских реквизитов к удалению!")
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            banks_details: List[Optional[BankDetails]] = await BankDetailsQueryAndStatementManager.get_banks_details(
                session=session,
                bank_details_ids=bank_details_ids
            )
            
            user_uuid_tuple = tuple(set([bank_details.user_uuid for bank_details in banks_details]))
            counterparty_uuid_tuple = tuple(set([bank_details.counterparty_uuid for bank_details in banks_details]))
            if len(user_uuid_tuple) != 1 or user_uuid_tuple[0] != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять записи о Реквизитах других Пользователей или же Реквизиты с данным id уже удалены!")
            
            if counterparty_uuid_tuple:
                if len(counterparty_uuid_tuple) != 1:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять записи о Реквизитах других Пользователей!")
                
                counterparty_check_access_response_object: Optional[Tuple[int, int, int, str]] = await CounterpartyQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    counterparty_uuid=counterparty_uuid_tuple[0],
                )
                if counterparty_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять записи о Реквизитах других Пользователей!")
        
        await BankDetailsQueryAndStatementManager.delete_banks_details(
            session=session,
            bank_details_ids=bank_details_ids,
        )
