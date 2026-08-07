from abc import ABC, abstractmethod
from .models import MarketSnapshot

class MarketParser(ABC):
    marketplace: str

    @abstractmethod
    async def snapshot(self) -> MarketSnapshot:
        raise NotImplementedError
