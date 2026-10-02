"""
CORS middleware configuration for Aurora backend.
"""

CORS_CONFIG = {
    "allow_origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
