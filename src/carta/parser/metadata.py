"""Extract conversation metadata from JSON exports."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def extract_conversation_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract primary metadata fields from conversation data."""
    return {
        'id': data.get('id'),
        'title': data.get('title', 'Untitled Conversation'),
        'create_time': data.get('create_time'),
        'update_time': data.get('update_time'),
        'default_model_slug': data.get('model', {}).get('slug') if data.get('model') else None
    }
