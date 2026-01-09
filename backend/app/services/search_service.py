import logging
import uuid
from typing import Any

from sqlmodel import Session

from app.services.dropbox_service import DropboxService
from app.services.integrations_service import IntegrationService
from app.services.one_drive_service import OneDriveService

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self) -> None:
        self.dropbox_service = DropboxService()
        self.one_drive_service = OneDriveService()
        self.google_drive_service = IntegrationService()

    async def search_all_providers(
        self,
        user_id: uuid.UUID,
        search_query: str,
        session: Session | None = None,
    ) -> dict[str, Any]:
        if not search_query or not search_query.strip():
            return {
                "query": search_query,
                "results": {
                    "dropbox": {"files": [], "total": 0, "error": None},
                    "one_drive": {"files": [], "total": 0, "error": None},
                    "google_drive": {"files": [], "total": 0, "error": None},
                },
                "total_files": 0,
            }

        search_query_lower = search_query.lower().strip()

        try:
            dropbox_results = await self._search_dropbox(
                user_id, search_query_lower, session
            )
            one_drive_results = await self._search_one_drive(
                user_id, search_query_lower, session
            )
            google_drive_results = await self._search_google_drive(
                user_id, search_query_lower, session
            )
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "query": search_query,
                "results": {
                    "dropbox": {"files": [], "total": 0, "error": str(e)},
                    "one_drive": {"files": [], "total": 0, "error": str(e)},
                    "google_drive": {"files": [], "total": 0, "error": str(e)},
                },
            }
        return {
            "query": search_query,
            "results": {
                "dropbox": dropbox_results,
                "one_drive": one_drive_results,
                "google_drive": google_drive_results,
            },
        }

    async def _search_dropbox(
        self,
        user_id: uuid.UUID,
        search_query: str,
        session: Session | None = None,
    ) -> dict[str, Any]:
        try:
            matching_files = await self.dropbox_service.search_files(
                user_id=user_id,
                query=search_query,
                session=session,
            )
            logger.debug(f"DROPBOX SEARCH RESULTS: {len(matching_files)} files found")
            for file in matching_files:
                file["provider"] = "dropbox"
                file["match_type"] = "both"

            return {
                "files": matching_files,
                "total": len(matching_files),
                "error": None,
            }
        except Exception as e:
            logger.error(f"Error searching Dropbox: {e}")
            return {"files": [], "total": 0, "error": str(e)}

    async def _search_one_drive(
        self,
        user_id: uuid.UUID,
        search_query: str,
        session: Session | None = None,
    ) -> dict[str, Any]:
        try:
            matching_files = await self.one_drive_service.search_files(
                user_id=user_id,
                query=search_query,
                session=session,
            )

            for file in matching_files:
                file["provider"] = "one_drive"
                file["match_type"] = "both"

            return {
                "files": matching_files,
                "total": len(matching_files),
                "error": None,
            }
        except Exception as e:
            logger.error(f"Error searching OneDrive: {e}")
            return {"files": [], "total": 0, "error": str(e)}

    async def _search_google_drive(
        self,
        user_id: uuid.UUID,
        search_query: str,
        session: Session | None = None,
    ) -> dict[str, Any]:
        try:
            matching_files = await self.google_drive_service.search_google_drive_files(
                user_id=user_id,
                query=search_query,
                session=session,
            )
            logger.debug(
                f"GOOGLE DRIVE SEARCH RESULTS: {len(matching_files)} files found"
            )
            for file in matching_files:
                file["provider"] = "google_drive"
                file["match_type"] = "both"

            return {
                "files": matching_files,
                "total": len(matching_files),
                "error": None,
            }
        except Exception as e:
            logger.error(f"Error searching Google Drive: {e}")
            return {"files": [], "total": 0, "error": str(e)}
