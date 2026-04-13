from abc import ABC, abstractmethod
from src.extraction.schemas import ExtractionRequest, ExtractionResult

class BaseExtractor(ABC):
    @abstractmethod
    async def extract(self, req: ExtractionRequest) -> ExtractionResult:
        """Processes a file and returns extracted transaction data in canonical format."""
        pass
