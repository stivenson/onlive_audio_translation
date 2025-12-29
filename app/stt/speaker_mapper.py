"""Speaker ID to User role mapping."""

from typing import Dict, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class SpeakerMapper:
    """Maps speaker IDs to User roles (User_1, User_2, etc.)."""
    
    def __init__(self, smoothing_window: int = 3):
        """
        Initialize speaker mapper.
        
        Args:
            smoothing_window: Number of recent assignments to consider for smoothing
        """
        self.smoothing_window = smoothing_window
        self.speaker_to_user: Dict[str, str] = {}
        self.user_counter = 1
        self.recent_assignments: Dict[str, list] = defaultdict(list)
    
    def get_user_role(self, speaker_id: Optional[str]) -> str:
        """
        Get User role for a speaker ID.
        
        Args:
            speaker_id: Speaker ID from STT provider (or None)
            
        Returns:
            User role string (e.g., "User_1", "User_2")
        """
        if speaker_id is None:
            return "Unknown"
        
        # Check if we already have a mapping
        if speaker_id in self.speaker_to_user:
            user_role = self.speaker_to_user[speaker_id]
            # Track recent assignment for smoothing
            self.recent_assignments[speaker_id].append(user_role)
            if len(self.recent_assignments[speaker_id]) > self.smoothing_window:
                self.recent_assignments[speaker_id].pop(0)
            return user_role
        
        # New speaker - assign next User role
        user_role = f"User_{self.user_counter}"
        self.speaker_to_user[speaker_id] = user_role
        self.user_counter += 1
        self.recent_assignments[speaker_id].append(user_role)
        
        logger.info(f"Mapped speaker {speaker_id} to {user_role}")
        return user_role
    
    def reset(self):
        """Reset all mappings."""
        self.speaker_to_user.clear()
        self.recent_assignments.clear()
        self.user_counter = 1
        logger.info("Speaker mappings reset")

