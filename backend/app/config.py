"""Server-only configuration. No demo credential belongs in browser code."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    project_id: str = ""
    model_id: str = "gemini-3.5-flash-lite"
    bucket: str = ""
    a2a_url: str = ""
    demo_username: str = ""
    password_hash: str = ""
    app_origin: str = "http://localhost:5173"
    secure_cookies: bool = True
    agent_enabled: bool = True
    a2a_iam_auth: bool = True
    model_location: str = "global"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            model_id=os.getenv("CUSTRA_MODEL_ID", "gemini-3.5-flash-lite"),
            bucket=os.getenv("CUSTRA_BUCKET", ""),
            a2a_url=os.getenv("CUSTRA_A2A_URL", ""),
            demo_username=os.getenv("CUSTRA_DEMO_USERNAME", ""),
            password_hash=os.getenv("CUSTRA_DEMO_PASSWORD_HASH", ""),
            app_origin=os.getenv("CUSTRA_APP_ORIGIN", "http://localhost:5173"),
            secure_cookies=os.getenv("CUSTRA_SECURE_COOKIES", "true").lower() == "true",
            agent_enabled=os.getenv("CUSTRA_AGENT_ENABLED", "true").lower() == "true",
            a2a_iam_auth=os.getenv("CUSTRA_A2A_IAM", "true").lower() == "true",
            model_location=os.getenv("GOOGLE_CLOUD_LOCATION", "global"),
        )
