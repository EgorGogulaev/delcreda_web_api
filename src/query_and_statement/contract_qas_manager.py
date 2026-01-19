# TODO Реализовать

from typing import Optional, Tuple
from sqlalchemy import and_, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contract_models import Contract
from src.utils.reference_mapping_data.contract.mapping import CONTRACT_TYPE_MAPPING
from utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING


class ContractQueryAndStatementManager:
    @staticmethod
    async def create_contract(
        session: AsyncSession,
        
        uuid: str,
        name: str,
        type: str,
        user_id: int,
        user_uuid: str,
        counterparty_id: int,
        counterparty_uuid: str,
        application_id: Optional[int],
        application_uuid: Optional[str],
        document_uuid: str,
        start_date: Optional[str],
        expiration_date: Optional[str],
    ) -> None:
        stmt = (
            insert(Contract)
            .values(
                uuid=uuid,
                name=name,
                type=CONTRACT_TYPE_MAPPING[type],
                user_id=user_id,
                user_uuid=user_uuid,
                counterparty_id=counterparty_id,
                counterparty_uuid=counterparty_uuid,
                application_id=application_id,
                application_uuid=application_uuid,
                document_uuid=document_uuid,
                start_date=start_date,
                expiration_date=expiration_date,
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def get_contracts():
        ...  # TODO
    
    @staticmethod
    async def check_access(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        contract_uuid: str,
    ) -> Optional[Tuple[int, str]]:
        _filters = [Contract.uuid == contract_uuid]
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(Contract.user_uuid == requester_user_uuid)
        
        query = (
            select(Contract.id, Contract.uuid)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        response = await session.execute(query)
        result = response.one_or_none()
        
        return result
    
    @staticmethod
    async def update_contract():
        ...  # TODO
    
    @staticmethod
    async def delete_contracts():
        ...  # TODO
