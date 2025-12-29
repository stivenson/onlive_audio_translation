"""Audio capture from system loopback."""

import asyncio
import platform
import logging
import unicodedata
from typing import Optional, Callable, List
import numpy as np

logger = logging.getLogger(__name__)

# Try to import pyaudio
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("PyAudio not available. Audio capture will not work.")


class AudioCapture:
    """Captures audio from system loopback (Windows) or virtual device (macOS)."""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 3200,
        device_index: Optional[int] = None
    ):
        """
        Initialize audio capture.
        
        Args:
            sample_rate: Sample rate in Hz
            channels: Number of channels (1 = mono)
            chunk_size: Frames per buffer
            device_index: Specific device index (None = default)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index
        
        self.audio = None
        self.stream = None
        self.is_capturing = False
        self.callback: Optional[Callable[[bytes], None]] = None
    
    def list_devices(self) -> List[dict]:
        """
        List available audio devices.
        
        Returns:
            List of device info dictionaries
        """
        if not PYAUDIO_AVAILABLE:
            return []
        
        devices = []
        audio = pyaudio.PyAudio()
        
        try:
            info = audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            
            for i in range(num_devices):
                try:
                    device_info = audio.get_device_info_by_host_api_device_index(0, i)
                    
                    # Check if device supports input
                    if device_info.get('maxInputChannels') > 0:
                        devices.append({
                            'index': i,
                            'name': device_info.get('name'),
                            'channels': device_info.get('maxInputChannels'),
                            'sample_rate': int(device_info.get('defaultSampleRate'))
                        })
                except Exception as e:
                    logger.debug(f"Error getting device {i} info: {e}")
        
        finally:
            audio.terminate()
        
        return devices
    
    def find_loopback_device(self) -> Optional[int]:
        """
        Find loopback device for system audio capture.
        
        Returns:
            Device index or None if not found
        """
        if not PYAUDIO_AVAILABLE:
            return None
        
        system = platform.system()
        devices = self.list_devices()
        
        def _norm(s: str) -> str:
            # Lowercase + strip accents for robust matching (e.g. "Mezcla estéreo")
            s = s.lower()
            return "".join(
                ch for ch in unicodedata.normalize("NFKD", s)
                if not unicodedata.combining(ch)
            )
        
        if system == "Windows":
            # On Windows, look for "Stereo Mix" or similar loopback devices
            for device in devices:
                name_raw = device.get("name") or ""
                name = _norm(name_raw)
                # Common labels across locales/drivers:
                # - "Stereo Mix"
                # - "Mezcla estéreo" (Spanish)
                # - "What U Hear"
                if (
                    "stereo mix" in name
                    or ("stereo" in name and "mix" in name)
                    or "mezcla estereo" in name
                    or ("mezcla" in name and "estereo" in name)
                    or "what u hear" in name
                    or "loopback" in name
                ):
                    logger.info(f"Found loopback device: {device['name']}")
                    return device['index']
            
            # If no explicit loopback found, try WASAPI loopback
            # PyAudio doesn't directly support WASAPI loopback, but we can try
            # the default input device which might be configured as loopback
            logger.warning("No explicit loopback device found. Using default input device.")
            return None
        
        elif system == "Darwin":  # macOS
            # On macOS, look for BlackHole or similar virtual devices
            for device in devices:
                name = device['name'].lower()
                if 'blackhole' in name or 'soundflower' in name or 'loopback' in name:
                    logger.info(f"Found virtual audio device: {device['name']}")
                    return device['index']
            
            logger.warning(
                "No virtual audio device found. Please install BlackHole: "
                "https://github.com/ExistentialAudio/BlackHole"
            )
            return None
        
        return None
    
    def find_realtek_device(self) -> Optional[int]:
        """
        Find Realtek audio device.
        
        Returns:
            Device index or None if not found
        """
        if not PYAUDIO_AVAILABLE:
            return None
        
        devices = self.list_devices()
        
        # Look for Realtek devices (case-insensitive)
        for device in devices:
            name = device['name'].lower()
            if 'realtek' in name:
                logger.info(f"Found Realtek device: {device['name']}")
                return device['index']
        
        logger.debug("No Realtek device found.")
        return None
    
    def start_capture(self, callback: Callable[[bytes], None]):
        """
        Start capturing audio.
        
        Args:
            callback: Function to call with audio chunks (bytes)
        """
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not available. Cannot capture audio.")
        
        if self.is_capturing:
            logger.warning("Already capturing audio")
            return
        
        self.callback = callback
        self.audio = pyaudio.PyAudio()
        
        # Use specified device index, or try to find loopback device if not specified
        device_index = self.device_index
        if device_index is None:
            device_index = self.find_loopback_device()
        
        logger.info(f"Using audio device index: {device_index}")
        
        try:
            # Open audio stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.stream.start_stream()
            self.is_capturing = True
            logger.info(f"Audio capture started (device: {device_index}, rate: {self.sample_rate}Hz)")
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            self.cleanup()
            raise
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Internal callback for audio stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        if self.callback and in_data:
            try:
                # Log first few chunks to verify audio is being captured
                if not hasattr(self, '_chunk_count'):
                    self._chunk_count = 0
                self._chunk_count += 1
                
                if self._chunk_count <= 3 or self._chunk_count % 100 == 0:
                    logger.debug(f"Audio chunk {self._chunk_count}: {len(in_data)} bytes")
                
                self.callback(in_data)
            except Exception as e:
                logger.error(f"Error in audio callback: {e}")
        
        return (None, pyaudio.paContinue)
    
    def stop_capture(self):
        """Stop capturing audio."""
        if not self.is_capturing:
            return
        
        self.is_capturing = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
        
        self.cleanup()
        logger.info("Audio capture stopped")
    
    def cleanup(self):
        """Clean up audio resources."""
        if self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                logger.error(f"Error terminating audio: {e}")
            finally:
                self.audio = None
        self.stream = None
        self.callback = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_capture()
        self.cleanup()

