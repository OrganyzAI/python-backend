import asyncio
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
        search_in_content: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB default
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

        # Search all providers in parallel
        dropbox_task = self._search_dropbox(
            user_id, search_query_lower, search_in_content, max_file_size, session
        )
        one_drive_task = self._search_one_drive(
            user_id, search_query_lower, search_in_content, max_file_size, session
        )
        google_drive_task = self._search_google_drive(
            user_id, search_query_lower, search_in_content, max_file_size, session
        )

        dropbox_results, one_drive_results, google_drive_results = await asyncio.gather(
            dropbox_task, one_drive_task, google_drive_task, return_exceptions=True
        )

        # Handle exceptions
        if isinstance(dropbox_results, Exception):
            logger.error(f"Dropbox search error: {dropbox_results}")
            dropbox_results = {"files": [], "total": 0, "error": str(dropbox_results)}
        if isinstance(one_drive_results, Exception):
            logger.error(f"OneDrive search error: {one_drive_results}")
            one_drive_results = {
                "files": [],
                "total": 0,
                "error": str(one_drive_results),
            }
        if isinstance(google_drive_results, Exception):
            logger.error(f"Google Drive search error: {google_drive_results}")
            google_drive_results = {
                "files": [],
                "total": 0,
                "error": str(google_drive_results),
            }

        total_files = (
            dropbox_results.get("total", 0)
            + one_drive_results.get("total", 0)
            + google_drive_results.get("total", 0)
        )

        return {
            "query": search_query,
            "results": {
                "dropbox": dropbox_results,
                "one_drive": one_drive_results,
                "google_drive": google_drive_results,
            },
            "total_files": total_files,
        }

    async def _search_dropbox(
        self,
        user_id: uuid.UUID,
        search_query: str,
        search_in_content: bool,
        max_file_size: int,
        session: Session | None = None,
    ) -> dict[str, Any]:
        try:
            # Use native Dropbox search API (searches both filename and content)
            matching_files = await self.dropbox_service.search_files(
                user_id=user_id,
                query=search_query,
                search_in_content=search_in_content,
                session=session,
            )

            # Add provider and match_type to each result
            for file in matching_files:
                file["provider"] = "dropbox"
                # Dropbox search API searches both filename and content, so we mark as "both"
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
        search_in_content: bool,
        max_file_size: int,
        session: Session | None = None,
    ) -> dict[str, Any]:
        try:
            # Use native Microsoft Graph search API (searches both filename and content)
            matching_files = await self.one_drive_service.search_files(
                user_id=user_id,
                query=search_query,
                search_in_content=search_in_content,
                session=session,
            )

            # Add provider and match_type to each result
            for file in matching_files:
                file["provider"] = "one_drive"
                # Microsoft Graph search API searches both filename and content, so we mark as "both"
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
        search_in_content: bool,
        max_file_size: int,
        session: Session | None = None,
    ) -> dict[str, Any]:
        try:
            # Use native Google Drive search API (searches both filename and content)
            matching_files = await self.google_drive_service.search_google_drive_files(
                user_id=user_id,
                query=search_query,
                search_in_content=search_in_content,
                session=session,
            )

            # Add provider and match_type to each result
            for file in matching_files:
                file["provider"] = "google_drive"
                # Google Drive search API searches both filename and content, so we mark as "both"
                file["match_type"] = "both"

            return {
                "files": matching_files,
                "total": len(matching_files),
                "error": None,
            }
        except Exception as e:
            logger.error(f"Error searching Google Drive: {e}")
            return {"files": [], "total": 0, "error": str(e)}
