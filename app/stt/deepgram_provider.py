"""Deepgram STT provider implementation."""

import asyncio
import json
from typing import Optional, AsyncIterator
import logging

try:
    from deepgram import DeepgramClient, DeepgramClientOptions, PrerecordedOptions
    from deepgram.clients.listen.v1 import ListenOptions
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False

from app.stt.base import STTProvider
from app.core.schemas import TranscriptEvent, TranscriptType

logger = logging.getLogger(__name__)


class DeepgramProvider(STTProvider):
    """Deepgram streaming STT provider."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        
        if not DEEPGRAM_AVAILABLE:
            raise ImportError("deepgram-sdk not installed")
        
        if not api_key:
            raise ValueError("Deepgram API key required")
        
        options = DeepgramClientOptions(
            verbose=kwargs.get("verbose", False)
        )
        self.client = DeepgramClient(api_key, options)
        self.connection = None
    
    async def stream(
        self,
        audio_stream: AsyncIterator[bytes],
        sample_rate: int = 16000,
        language: Optional[str] = None,
        diarize: bool = True,
        punctuate: bool = True
    ) -> AsyncIterator[TranscriptEvent]:
        """
        Stream audio to Deepgram and yield transcript events.
        """
        try:
            # Configure options
            options = ListenOptions(
                model="nova-2",
                language=language or "en",
                punctuate=punctuate,
                diarize=diarize,
                smart_format=True,
                interim_results=True
            )
            
            # Create connection
            self.connection = self.client.listen.v("1").stream(options)
            
            # Start streaming
            async def send_audio():
                try:
                    async for audio_chunk in audio_stream:
                        if self.connection:
                            self.connection.send(audio_chunk)
                    # Signal end of stream
                    if self.connection:
                        await self.connection.finish()
                except Exception as e:
                    logger.error(f"Error sending audio to Deepgram: {e}")
                    if self.connection:
                        await self.connection.finish()
            
            # Start sending audio in background
            send_task = asyncio.create_task(send_audio())
            
            # Receive transcripts
            try:
                async for message in self.connection:
                    if message:
                        transcript = json.loads(message)
                        
                        # Parse Deepgram response
                        if "channel" in transcript:
                            channel = transcript["channel"]
                            alternatives = channel.get("alternatives", [])
                            
                            if alternatives:
                                alt = alternatives[0]
                                text = alt.get("transcript", "")
                                is_final = transcript.get("is_final", False)
                                
                                # Get speaker if diarization enabled
                                speaker_id = None
                                if diarize and "words" in alt:
                                    words = alt["words"]
                                    if words and "speaker" in words[0]:
                                        speaker_id = str(words[0]["speaker"])
                                
                                # Get timestamps
                                start_time = 0.0
                                end_time = 0.0
                                if "words" in alt and alt["words"]:
                                    start_time = alt["words"][0].get("start", 0.0)
                                    end_time = alt["words"][-1].get("end", 0.0)
                                
                                # Get confidence
                                confidence = alt.get("confidence", None)
                                
                                # Yield event
                                event = TranscriptEvent(
                                    text=text,
                                    transcript_type=TranscriptType.FINAL if is_final else TranscriptType.INTERIM,
                                    speaker_id=speaker_id,
                                    start_time=start_time,
                                    end_time=end_time,
                                    confidence=confidence,
                                    language=language or "en"
                                )
                                
                                yield event
                
            finally:
                # Wait for send task to complete
                if not send_task.done():
                    send_task.cancel()
                    try:
                        await send_task
                    except asyncio.CancelledError:
                        pass
        
        except Exception as e:
            logger.error(f"Deepgram streaming error: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check Deepgram API health."""
        try:
            # Simple health check - try to create a client
            # In a real implementation, you might make a test API call
            return self.client is not None and self.api_key is not None
        except Exception as e:
            logger.error(f"Deepgram health check failed: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return "deepgram"
    
    async def close(self):
        """Close Deepgram connection."""
        if self.connection:
            try:
                await self.connection.finish()
            except Exception as e:
                logger.error(f"Error closing Deepgram connection: {e}")
            finally:
                self.connection = None

