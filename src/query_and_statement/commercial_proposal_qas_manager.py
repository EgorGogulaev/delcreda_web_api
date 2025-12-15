import datetime
from typing import List, Literal, Optional, Tuple

from sqlalchemy import and_, insert, select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.commercial_proposal_models import CommercialProposal
from src.utils.reference_mapping_data.user.mapping import PRIVILEGE_MAPPING
from src.utils.reference_mapping_data.commercial_proposal.mapping import COMMERCIAL_PROPOSAL_STATUS_MAPPING


class CommercialProposalQueryAndStatementManager:
    ...  # TODO
    @staticmethod
    async def create_commercial_proposal(
        session: AsyncSession,
        
        new_commercial_proposal_uuid: str,
        commercial_proposal_name: Optional[str],
        type: Literal[
            "MT",
            # TODO
        ],
        
        user_id,
        target_user_uuid: str,
        
        counterparty_id: int,
        counterparty_uuid: str,
        application_id: Optional[int],
        application_uuid: Optional[str],
        directory_id: int,
        directory_uuid: str,
        
        document_uuid: Optional[str],
        
    ) -> None:
        
        stmt = (
            insert(CommercialProposal)
            .values(
                uuid=new_commercial_proposal_uuid,
                appliaction_name=commercial_proposal_name if commercial_proposal_name else f"{counterparty_id}-{directory_id}-{datetime.datetime.now().year}",
                commercial_proposal_name=commercial_proposal_name,
                type=type,
                user_id=user_id,
                user_uuid=target_user_uuid,
                counterparty_id=counterparty_id,
                counterparty_uuid=counterparty_uuid,
                application_id=application_id,
                application_uuid=application_uuid,
                directory_id=directory_id,
                directory_uuid=directory_uuid,
                document_uuid=document_uuid,
                status=COMMERCIAL_PROPOSAL_STATUS_MAPPING["На рассмотрении сторон"],
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    # TODO
    @staticmethod
    async def update_commercial_proposals_status(
        session: AsyncSession,
        
        commercial_proposal_uuids: List[str],
        new_status: bool,
    ) -> None:
        stmt = (
            update(CommercialProposal)
            .where(CommercialProposal.uuid.in_(commercial_proposal_uuids))
            .values(
                status=COMMERCIAL_PROPOSAL_STATUS_MAPPING[new_status],
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def change_commercial_proposals_edit_status(
        session: AsyncSession,
        
        commercial_proposal_uuids: List[str],
        edit_status: bool,
    ) -> None:
        stmt = (
            update(CommercialProposal)
            .where(CommercialProposal.uuid.in_(commercial_proposal_uuids))
            .values(
                can_be_updated_by_user=edit_status,
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def delete_commercial_proposals(
        session: AsyncSession,
        
        commercial_proposal_uuids: Optional[List[str]],
        commercial_proposal_ids: Optional[List[int]],
    ) -> None:
        _filters = []
        
        if commercial_proposal_uuids:
            _filters.append(CommercialProposal.uuid.in_(commercial_proposal_uuids))
        
        if commercial_proposal_ids:
            _filters.append(CommercialProposal.id.in_(commercial_proposal_ids))
        
        stmt = (
            delete(CommercialProposal)
            .filter(
                and_(
                    *_filters
                )
            )
        )
        
        await session.execute(stmt)
        await session.commit()
    
    @staticmethod
    async def check_access(
        session: AsyncSession,
        
        requester_user_uuid: str,
        requester_user_privilege: int,
        
        commercial_proposal_uuid: str,
        
        for_update_or_delete_commercial_proposal: bool = False,
    ) -> Optional[Tuple[int, str]]:
        _filters = [CommercialProposal.uuid == commercial_proposal_uuid]
        
        if requester_user_privilege != PRIVILEGE_MAPPING["Admin"]:
            _filters.append(CommercialProposal.user_uuid == requester_user_uuid)
            if for_update_or_delete_commercial_proposal:
                _filters.append(CommercialProposal.can_be_updated_by_user == True)  # noqa: E712
        
        query = (
            select(CommercialProposal.id, CommercialProposal.directory_uuid, )
            .filter(
                and_(
                    *_filters
                )
            )
        )
        response = await session.execute(query)
        result = response.one_or_none()
        
        return result
