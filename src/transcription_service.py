import os
import logging
from faster_whisper import WhisperModel
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class TranscriptionService:
    _model = None

    def __init__(self, model_size="base"):
        """Initializes Whisper model reference"""
        self.model_size = model_size

    @property
    def model(self):
        if TranscriptionService._model is None:
            logger.info(f"Loading Whisper model ({self.model_size}) on local CPU (first use)...")
            TranscriptionService._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            logger.info("Whisper model loaded successfully.")
        return TranscriptionService._model

    def transcribe_audio(self, audio_file_path: str):
        """Transcribes local audio file using local CPU inference"""
        try:
            # WhatsApp often sends .ogg or .m4a; ensure ffmpeg is installed for conversion
            # WhisperModel usually handles many formats natively via ffmpeg
            segments, info = self.model.transcribe(audio_file_path, beam_size=5)
            
            # Combine all transcribed segments
            full_text = " ".join([segment.text for segment in segments])
            
            logger.info(f"Successfully transcribed audio ({info.language}): {full_text}")
            return full_text.strip(), info.language
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None, None
