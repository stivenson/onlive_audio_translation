"""Deepgram STT provider implementation."""

import asyncio
import json
from typing import Optional, AsyncIterator
import logging

try:
    from deepgram import (
        DeepgramClient,
        DeepgramClientOptions,
        LiveTranscriptionEvents,
        LiveOptions,
    )
    DEEPGRAM_AVAILABLE = True
    EVENTS_AVAILABLE = True
except ImportError:
    try:
        # Fallback for older v3 versions or different structures
        from deepgram import DeepgramClient
        from deepgram.clients.listen.v1 import LiveOptions
        DEEPGRAM_AVAILABLE = True
        
        # Try to find DeepgramClientOptions elsewhere
        try:
            from deepgram import DeepgramClientOptions
        except ImportError:
            DeepgramClientOptions = None
            
        # Try to find LiveTranscriptionEvents
        try:
            from deepgram import LiveTranscriptionEvents
            EVENTS_AVAILABLE = True
        except ImportError:
            try:
                from deepgram.clients.listen.v1 import LiveTranscriptionEvents
                EVENTS_AVAILABLE = True
            except ImportError:
                LiveTranscriptionEvents = None
                EVENTS_AVAILABLE = False
    except ImportError:
        DEEPGRAM_AVAILABLE = False
        EVENTS_AVAILABLE = False
        LiveTranscriptionEvents = None
        DeepgramClientOptions = None

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
        
        if DeepgramClientOptions:
            options_client = DeepgramClientOptions(
                verbose=kwargs.get("verbose", False)
            )
            self.client = DeepgramClient(api_key, options_client)
        else:
            self.client = DeepgramClient(api_key)
        self.connection = None

    async def _is_connected(self) -> bool:
        """
        Deepgram SDK compatibility: in some versions `is_connected` is a method,
        in others it's a boolean property, and in some it's a coroutine function.
        """
        if not self.connection:
            return False
        attr = getattr(self.connection, "is_connected", None)
        if attr is None:
            return False
        try:
            # Check if it's a coroutine function (returns a coroutine when called)
            if asyncio.iscoroutinefunction(attr):
                result = attr()
                return bool(await result)
            # Check if it's already a coroutine (was called but not awaited)
            elif asyncio.iscoroutine(attr):
                return bool(await attr)
            # Check if it's callable (regular method)
            elif callable(attr):
                result = attr()
                # If result is a coroutine, await it
                if asyncio.iscoroutine(result):
                    return bool(await result)
                return bool(result)
            # Otherwise it's a property
            else:
                return bool(attr)
        except Exception as e:
            logger.debug(f"Error checking connection status: {e}")
            return False
    
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
        # Queue to receive messages from Deepgram callbacks
        message_queue = asyncio.Queue()
        connection_closed = asyncio.Event()
        
        try:
            # Configure options
            # Note: encoding is automatically set to linear16 for PCM 16-bit audio
            options = LiveOptions(
                model="nova-2",
                language=language or "en",
                punctuate=punctuate,
                diarize=diarize,
                smart_format=True,
                interim_results=True,
                sample_rate=sample_rate,
                encoding="linear16"  # Explicitly set encoding for PCM 16-bit
            )
            logger.info(f"Deepgram options: model={options.model}, language={options.language}, sample_rate={options.sample_rate}, encoding={getattr(options, 'encoding', 'default')}")
            
            # Create connection using async websocket (better for asyncio/Qt integration)
            self.connection = self.client.listen.asyncwebsocket.v("1")
            
            # Get event loop for thread-safe operations
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            
            # Set up message handler
            message_count = [0]  # Use list to allow modification in nested function
            async def on_message(self_inner, result, **kwargs):
                """Handle incoming transcript messages from Deepgram."""
                try:
                    message_count[0] += 1
                    logger.info(f"*** Deepgram transcript {message_count[0]} received ***")
                    
                    # Log detailed structure for first few messages
                    if message_count[0] <= 3:
                        logger.info(f"Result type: {type(result)}")
                        logger.info(f"Result dir: {[x for x in dir(result) if not x.startswith('_')]}")
                        
                        # Try to access different attributes
                        if hasattr(result, 'channel'):
                            logger.info(f"Has channel attribute")
                            logger.info(f"Channel type: {type(result.channel)}")
                            if hasattr(result.channel, 'alternatives'):
                                logger.info(f"Has alternatives: {len(result.channel.alternatives)}")
                                if result.channel.alternatives:
                                    alt = result.channel.alternatives[0]
                                    logger.info(f"Alternative[0] type: {type(alt)}")
                                    logger.info(f"Alternative[0] dir: {[x for x in dir(alt) if not x.startswith('_')]}")
                                    if hasattr(alt, 'transcript'):
                                        logger.info(f"Transcript value: '{alt.transcript}'")
                        
                        # Try to convert to dict
                        if hasattr(result, 'to_dict'):
                            result_dict = result.to_dict()
                            logger.info(f"Result as dict keys: {list(result_dict.keys())}")
                            if 'channel' in result_dict:
                                logger.info(f"Channel dict: {result_dict['channel']}")
                    
                    # Log result type and summary
                    if hasattr(result, 'channel'):
                        # It's likely a LiveResult object
                        if hasattr(result.channel, 'alternatives') and result.channel.alternatives:
                            alt = result.channel.alternatives[0]
                            transcript = alt.transcript if hasattr(alt, 'transcript') else ""
                            is_final = result.is_final if hasattr(result, 'is_final') else False
                            logger.info(f"Transcript: '{transcript[:100]}', is_final={is_final}")
                        else:
                            logger.warning("No alternatives in channel")
                    else:
                        logger.info(f"Result type: {type(result).__name__}")
                    
                    # Put result in queue for async processing
                    try:
                        await message_queue.put(result)
                        logger.debug(f"Transcript {message_count[0]} queued successfully")
                    except Exception as queue_error:
                        logger.error(f"Error queuing transcript: {queue_error}")
                except Exception as e:
                    logger.error(f"Error handling Deepgram transcript: {e}", exc_info=True)
            
            async def on_error(self_inner, error, **kwargs):
                """Handle errors from Deepgram."""
                logger.error(f"Deepgram error: {error}")
                try:
                    await message_queue.put(None)  # Signal error
                except:
                    pass
            
            async def on_close(self_inner, **kwargs):
                """Handle connection close."""
                logger.info("Deepgram connection closed")
                try:
                    connection_closed.set()
                    await message_queue.put(None)  # Signal end
                except:
                    pass
            
            async def on_metadata(self_inner, metadata, **kwargs):
                """Handle metadata from Deepgram."""
                logger.info(f"Deepgram metadata received: {metadata}")
            
            async def on_open(self_inner, open_data, **kwargs):
                """Handle connection open."""
                logger.info(f"Deepgram connection opened: {open_data}")
                """Handle connection open."""
                logger.info(f"Deepgram connection opened: {open_data}")
            
            # Register event handlers
            logger.info("Registering Deepgram event handlers...")
            logger.info(f"EVENTS_AVAILABLE={EVENTS_AVAILABLE}, LiveTranscriptionEvents={LiveTranscriptionEvents}")
            
            # Register transcript handler using the proper event
            if EVENTS_AVAILABLE and LiveTranscriptionEvents:
                try:
                    logger.info(f"Using LiveTranscriptionEvents.Transcript")
                    self.connection.on(LiveTranscriptionEvents.Transcript, on_message)
                    logger.info("Successfully registered Transcript handler")
                except Exception as e:
                    logger.error(f"Failed to register Transcript handler: {e}", exc_info=True)
            else:
                logger.warning("LiveTranscriptionEvents not available, trying fallback methods")
                # Fallback to string event names
                for event_name in ["Transcript", "transcript", "message", "Message"]:
                    try:
                        self.connection.on(event_name, on_message)
                        logger.info(f"Registered handler for event: {event_name}")
                        break
                    except Exception as e:
                        logger.debug(f"Failed to register handler for '{event_name}': {e}")
            
            # Register error, close, metadata, and open handlers
            if EVENTS_AVAILABLE and LiveTranscriptionEvents:
                try:
                    if hasattr(LiveTranscriptionEvents, 'Error'):
                        self.connection.on(LiveTranscriptionEvents.Error, on_error)
                        logger.info("Registered Error handler")
                    if hasattr(LiveTranscriptionEvents, 'Close'):
                        self.connection.on(LiveTranscriptionEvents.Close, on_close)
                        logger.info("Registered Close handler")
                    if hasattr(LiveTranscriptionEvents, 'Metadata'):
                        self.connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
                        logger.info("Registered Metadata handler")
                    if hasattr(LiveTranscriptionEvents, 'Open'):
                        self.connection.on(LiveTranscriptionEvents.Open, on_open)
                        logger.info("Registered Open handler")
                except Exception as e:
                    logger.warning(f"Failed to register some event handlers: {e}")
            else:
                try:
                    self.connection.on("error", on_error)
                    self.connection.on("close", on_close)
                    logger.info("Registered error and close handlers (string events)")
                except Exception as e:
                    logger.warning(f"Failed to register error/close handlers: {e}")
            
            logger.info("Event handlers registered successfully")
            
            # Start the connection
            logger.info("Starting Deepgram connection...")
            start_result = await self.connection.start(options)
            if not start_result:
                raise RuntimeError("Failed to start Deepgram connection")
            logger.info("Deepgram connection started successfully")
            
            # Start sending audio in background
            send_count = [0]
            async def send_audio():
                try:
                    async for audio_chunk in audio_stream:
                        # Check if connection was closed
                        if connection_closed.is_set():
                            logger.info("Connection closed, stopping audio send")
                            break
                        
                        # Check connection status
                        if not self.connection:
                            logger.warning("Connection is None, stopping send")
                            break
                        
                        try:
                            is_connected = await self._is_connected()
                            if not is_connected:
                                logger.warning("Connection not connected, stopping send")
                                break
                            
                            # Try to send audio chunk
                            await self.connection.send(audio_chunk)
                            send_count[0] += 1
                            if send_count[0] <= 10:
                                # Log first 10 chunks with audio level info
                                import struct
                                if len(audio_chunk) >= 2:
                                    # Calculate RMS level for first few chunks
                                    audio_samples = struct.unpack(f'<{len(audio_chunk)//2}h', audio_chunk)
                                    rms = (sum(x*x for x in audio_samples) / len(audio_samples)) ** 0.5
                                    max_val = max(abs(x) for x in audio_samples) if audio_samples else 0
                                    logger.info(f"Sent audio chunk {send_count[0]} to Deepgram: {len(audio_chunk)} bytes, RMS={rms:.1f}, Max={max_val}")
                                else:
                                    logger.info(f"Sent audio chunk {send_count[0]} to Deepgram: {len(audio_chunk)} bytes")
                            elif send_count[0] % 100 == 0:
                                logger.debug(f"Sent audio chunk {send_count[0]} to Deepgram: {len(audio_chunk)} bytes")
                        except Exception as send_error:
                            # Connection likely closed - check and break
                            logger.warning(f"Error sending audio chunk: {send_error}")
                            if connection_closed.is_set():
                                logger.info("Connection was closed, stopping send")
                                break
                            # If it's a connection error, stop sending
                            error_str = str(send_error).lower()
                            if "connection" in error_str or "closed" in error_str or "1011" in error_str:
                                logger.warning("Connection error detected, stopping send")
                                break
                            # For other errors, continue but log
                            continue
                    
                    # Signal end of stream only if still connected
                    if self.connection and not connection_closed.is_set():
                        try:
                            is_connected = await self._is_connected()
                            if is_connected:
                                await self.connection.finish()
                        except Exception as e:
                            logger.debug(f"Error finishing connection: {e}")
                except asyncio.CancelledError:
                    logger.debug("Send audio task cancelled")
                    raise
                except Exception as e:
                    logger.error(f"Error in send_audio task: {e}")
                    # Don't try to finish if connection is already closed
                    if self.connection and not connection_closed.is_set():
                        try:
                            await self.connection.finish()
                        except:
                            pass
            
            send_task = asyncio.create_task(send_audio())
            
            # Receive and yield transcripts
            logger.info("Starting to receive transcripts from Deepgram...")
            
            # Also try to get messages directly from connection if available
            direct_message_task = None
            if hasattr(self.connection, 'get_message') or hasattr(self.connection, 'receive'):
                async def get_messages_directly():
                    """Try to get messages directly from connection."""
                    try:
                        while not connection_closed.is_set():
                            try:
                                if hasattr(self.connection, 'get_message'):
                                    msg = await asyncio.wait_for(self.connection.get_message(), timeout=0.5)
                                elif hasattr(self.connection, 'receive'):
                                    msg = await asyncio.wait_for(self.connection.receive(), timeout=0.5)
                                else:
                                    await asyncio.sleep(0.1)
                                    continue
                                
                                if msg:
                                    logger.info(f"Got message directly from connection: {type(msg)}")
                                    if loop.is_running():
                                        loop.call_soon_threadsafe(message_queue.put_nowait, msg)
                                    else:
                                        message_queue.put_nowait(msg)
                            except asyncio.TimeoutError:
                                continue
                            except Exception as e:
                                logger.debug(f"Error getting message directly: {e}")
                                await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.debug(f"Direct message task error: {e}")
                
                direct_message_task = asyncio.create_task(get_messages_directly())
                logger.info("Started direct message retrieval task")
            
            try:
                while True:
                    # Wait for message or connection close
                    try:
                        message = await asyncio.wait_for(
                            message_queue.get(), 
                            timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        # Check if connection is still alive
                        if connection_closed.is_set():
                            logger.warning("Connection closed, breaking message loop")
                            break
                        try:
                            is_connected = await self._is_connected()
                            if not is_connected:
                                logger.warning("Connection not connected, breaking message loop")
                                break
                        except Exception as e:
                            logger.debug(f"Error checking connection status: {e}")
                            # If we can't check, assume it's closed after timeout
                            if connection_closed.is_set():
                                break
                        # Log timeout occasionally to show we're still waiting
                        if not hasattr(self, '_timeout_count'):
                            self._timeout_count = 0
                        self._timeout_count += 1
                        # Log first few timeouts at INFO level, then periodically at DEBUG
                        if self._timeout_count <= 5:
                            try:
                                is_connected = await self._is_connected()
                                logger.info(f"Waiting for Deepgram messages (timeout {self._timeout_count}, connected={is_connected})...")
                            except:
                                logger.info(f"Waiting for Deepgram messages (timeout {self._timeout_count})...")
                        elif self._timeout_count % 10 == 0:
                            logger.debug(f"Waiting for Deepgram messages (timeout {self._timeout_count})...")
                        continue
                    
                    if message is None:
                        # End signal
                        break
                    
                    try:
                        # Parse Deepgram response
                        # The result is a LiveResultResponse object
                        text = ""
                        is_final = False
                        speaker_id = None
                        start_time = 0.0
                        end_time = 0.0
                        confidence = None
                        
                        try:
                            # Access the LiveResultResponse object attributes
                            if hasattr(message, 'channel') and message.channel:
                                if hasattr(message.channel, 'alternatives') and message.channel.alternatives:
                                    alt = message.channel.alternatives[0]
                                    
                                    # Get transcript text
                                    if hasattr(alt, 'transcript'):
                                        text = alt.transcript.strip() if alt.transcript else ""
                                    
                                    # Get confidence
                                    if hasattr(alt, 'confidence'):
                                        confidence = alt.confidence
                                    
                                    # Get speaker ID from words if diarization enabled
                                    if diarize and hasattr(alt, 'words') and alt.words:
                                        first_word = alt.words[0]
                                        if hasattr(first_word, 'speaker'):
                                            speaker_id = str(first_word.speaker)
                                        
                                        # Get timestamps from words
                                        if hasattr(alt.words[0], 'start'):
                                            start_time = alt.words[0].start
                                        if hasattr(alt.words[-1], 'end'):
                                            end_time = alt.words[-1].end
                                
                                # Get is_final from the result
                                if hasattr(message, 'is_final'):
                                    is_final = message.is_final
                            
                            # Skip empty transcripts
                            if not text:
                                # Log occasionally to show we're filtering empty transcripts
                                if not hasattr(self, '_empty_count'):
                                    self._empty_count = 0
                                self._empty_count += 1
                                if self._empty_count <= 5 or self._empty_count % 20 == 0:
                                    logger.info(f"Skipping empty transcript {self._empty_count} (is_final={is_final}, confidence={confidence})")
                                continue
                            
                            # Reset empty count when we get real text
                            if hasattr(self, '_empty_count'):
                                self._empty_count = 0
                            
                            # Yield the transcript event
                            logger.info(f"✅ Yielding transcript: '{text[:100]}', is_final={is_final}, speaker={speaker_id}, confidence={confidence}")
                            yield TranscriptEvent(
                                text=text,
                                transcript_type=TranscriptType.FINAL if is_final else TranscriptType.INTERIM,
                                speaker_id=speaker_id,
                                start_time=start_time,
                                end_time=end_time,
                                confidence=confidence,
                                language=language or "en"
                            )
                        except Exception as e:
                            logger.error(f"Error parsing Deepgram message: {e}", exc_info=True)
                            continue
                        else:
                            # Message doesn't have channel key - might be metadata or other message type
                            logger.debug(f"Received message without 'channel' key. Keys: {list(transcript.keys())}")
                    except Exception as e:
                        logger.error(f"Error parsing Deepgram message: {e}")
                        continue
                
            finally:
                # Signal connection closed to stop send task
                connection_closed.set()
                
                # Cancel direct message task if it exists
                if direct_message_task and not direct_message_task.done():
                    direct_message_task.cancel()
                    try:
                        await direct_message_task
                    except (asyncio.CancelledError, Exception):
                        pass
                
                # Wait for send task to complete
                if not send_task.done():
                    send_task.cancel()
                    try:
                        await send_task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.debug(f"Error waiting for send task: {e}")
                
                # Clean up connection
                if self.connection:
                    try:
                        await self.connection.finish()
                    except Exception as e:
                        logger.debug(f"Error finishing connection in finally: {e}")
        
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

