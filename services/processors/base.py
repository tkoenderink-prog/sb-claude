"""Base processor class for all data processors."""
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel


class ProcessorResult(BaseModel):
    """Result of a processor run."""
    success: bool
    processor_name: str
    started_at: datetime
    ended_at: datetime
    output_path: Optional[str] = None
    error: Optional[str] = None
    metrics: dict[str, Any] = {}


class BaseProcessor(ABC):
    """Abstract base class for all processors."""

    def __init__(self, exports_path: Path, name: str):
        self.exports_path = exports_path
        self.name = name

    @abstractmethod
    async def run(self) -> ProcessorResult:
        """Execute the processor. Must be implemented by subclasses."""
        pass

    def get_output_path(self, filename: str) -> Path:
        """Get path for output file in exports directory."""
        output_dir = self.exports_path / "normalized"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / filename
