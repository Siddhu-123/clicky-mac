"""STT Provider base class."""
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class BaseSTTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribes raw audio array into text."""
        pass
