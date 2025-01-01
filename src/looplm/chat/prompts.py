# src/looplm/chat/prompts.py

import json
from pathlib import Path
from typing import Dict

DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant"""


class PromptsManager:
    """Manages system prompts configuration"""

    def __init__(self):
        """Initialize prompts manager"""
        self.config_dir = Path.home() / ".looplm" / "prompts"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_file = self.config_dir / "prompts.json"

        # Create default prompts if file doesn't exist
        if not self.prompts_file.exists():
            self.save_prompts(
                {
                    "default": DEFAULT_SYSTEM_PROMPT,
                }
            )

    def load_prompts(self) -> Dict[str, str]:
        """Load saved prompts"""
        try:
            if self.prompts_file.exists():
                return json.loads(self.prompts_file.read_text())
            return {"default": DEFAULT_SYSTEM_PROMPT}
        except Exception:
            return {"default": DEFAULT_SYSTEM_PROMPT}

    def save_prompts(self, prompts: Dict[str, str]):
        """Save prompts to file"""
        self.prompts_file.write_text(json.dumps(prompts, indent=2))

    def get_prompt(self, name: str = "default") -> str:
        """Get a specific prompt"""
        prompts = self.load_prompts()
        return prompts.get(name, DEFAULT_SYSTEM_PROMPT)

    def save_prompt(self, name: str, prompt: str):
        """Save a new prompt"""
        prompts = self.load_prompts()
        prompts[name] = prompt
        self.save_prompts(prompts)

    def delete_prompt(self, name: str) -> bool:
        """Delete a saved prompt"""
        if name == "default":
            return False

        prompts = self.load_prompts()
        if name in prompts:
            del prompts[name]
            self.save_prompts(prompts)
            return True
        return False

    def list_prompts(self) -> Dict[str, str]:
        """Get all saved prompts"""
        return self.load_prompts()
