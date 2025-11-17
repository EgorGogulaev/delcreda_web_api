from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.legal_entity.bank_details_models import BankDetails
from src.query_and_statement.legal_entity.bank_details_qas_manager import BankDetailsQueryAndStatementManager
from src.query_and_statement.legal_entity.legal_entity_qas_manager import LegalEntityQueryAndStatementManager
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.schemas.legal_entity.bank_details_schema import CreateBanksDetailsSchema


class BankDetailsService:
    @staticmethod
    async def create_banks_details(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        new_banks_details: CreateBanksDetailsSchema,
    ) -> None:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            le_uuid_tuple = tuple(set([new_bank_details.legal_entity_uuid for new_bank_details in new_banks_details.new_banks_details]))
            if len(le_uuid_tuple) != 1:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете добавлять реквизиты к ЮЛ других Пользователей!")
            
            le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                session=session,
                
                requester_user_uuid=requester_user_uuid,
                requester_user_privilege=requester_user_privilege,
                legal_entity_uuid=le_uuid_tuple[0],
            )
            if le_check_access_response_object is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете добавлять реквизиты к ЮЛ других Пользователей!")
        
        await BankDetailsQueryAndStatementManager.create_banks_details(
            session=session,
            new_banks_details=new_banks_details,
        )
    
    @staticmethod
    async def get_banks_details(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        legal_entity_uuid: Optional[str] = None,
        user_uuid: Optional[str] = None,
    ) -> List[Optional[BankDetails]]:
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            if not legal_entity_uuid and not user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Реквизиты других Пользователей!")
            if user_uuid:
                if requester_user_uuid != user_uuid:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть Реквизиты других Пользователей!")
            if legal_entity_uuid:
                le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    legal_entity_uuid=legal_entity_uuid,
                )
                if le_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете просмотреть информацию о Реквизитах в ЮЛ других Пользователей!")
        
        banks_details: List[Optional[BankDetails]] = await BankDetailsQueryAndStatementManager.get_banks_details(
            session=session,
            
            legal_entity_uuid=legal_entity_uuid,
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
        legal_entity_uuid: Optional[str],
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
            if bank_details[0].legal_entity_uuid:
                le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    legal_entity_uuid=bank_details[0].legal_entity_uuid,
                )
                if le_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете обновить информацию о Реквизитах в ЮЛ других Пользователей!")
        
        if all(field == "~" for field in [
                user_uuid, legal_entity_uuid,
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
            legal_entity_uuid=legal_entity_uuid,
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
            le_uuid_tuple = tuple(set([bank_details.legal_entity_uuid for bank_details in banks_details]))
            if len(user_uuid_tuple) != 1 or user_uuid_tuple[0] != requester_user_uuid:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять записи о Реквизитах других Пользователей или же Реквизиты с данным id уже удалены!")
            
            if le_uuid_tuple:
                if len(le_uuid_tuple) != 1:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять записи о Реквизитах других Пользователей!")
                
                le_check_access_response_object: Optional[Tuple[int, int, str]] = await LegalEntityQueryAndStatementManager.check_access(
                    session=session,
                    
                    requester_user_uuid=requester_user_uuid,
                    requester_user_privilege=requester_user_privilege,
                    legal_entity_uuid=le_uuid_tuple[0],
                )
                if le_check_access_response_object is None:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Вы не можете удалять записи о Реквизитах других Пользователей!")
        
        await BankDetailsQueryAndStatementManager.delete_banks_details(
            session=session,
            bank_details_ids=bank_details_ids,
        )
