"""Abstract interface shared by every cloud storage provider."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional


class CloudError(Exception):
    """Raised for any provider-level failure (auth, network, API errors)."""


@dataclass
class CloudFile:
    """A file or folder entry returned by a provider."""

    id: str
    name: str
    is_folder: bool = False
    mime_type: str = ""
    modified_time: str = ""
    size: Optional[int] = None
    # Provider-specific handle used for navigation (e.g. a parent path).
    extra: Optional[dict] = None

    @property
    def display_name(self) -> str:
        return f"[{self.name}]" if self.is_folder else self.name


class CloudProvider(abc.ABC):
    """Common contract implemented by each cloud backend.

    Implementations must be safe to construct without network access; all
    network work happens inside :meth:`authenticate` and the file operations.
    """

    #: Short machine name, e.g. "gdrive".
    id: str = ""
    #: Human-facing name shown in menus, e.g. "Google Drive".
    name: str = ""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Whether the provider's optional dependencies are installed."""

    @abc.abstractmethod
    def is_authenticated(self) -> bool:
        """Whether a usable cached credential already exists."""

    @abc.abstractmethod
    def authenticate(self) -> None:
        """Perform (or refresh) authentication. Raises :class:`CloudError`."""

    @abc.abstractmethod
    def list_files(self, folder_id: Optional[str] = None) -> list[CloudFile]:
        """List children of ``folder_id`` (root when ``None``)."""

    @abc.abstractmethod
    def download(self, file_id: str) -> bytes:
        """Return the raw bytes of the file identified by ``file_id``."""

    @abc.abstractmethod
    def upload(
        self,
        name: str,
        content: bytes,
        file_id: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> CloudFile:
        """Create or overwrite a file.

        When ``file_id`` is given the existing file is updated in place;
        otherwise a new file called ``name`` is created inside ``folder_id``
        (or the account root when ``folder_id`` is ``None``).
        """

    def sign_out(self) -> None:  # pragma: no cover - optional override
        """Discard cached credentials. Providers override as needed."""
