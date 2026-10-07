"""AI Manager for Craft Framework.

Category: Core Framework (AI).
Relations:
  - Backs `craft.facades.AI`.
  - Resolves drivers from `config/ai.py`.
References:
  - Guide: `documentation/ai.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

from engine.ai.agent import AIAgent
from engine.ai.contracts import AIDriver, AIResponse, EmbeddingResponse
from engine.ai.drivers.gemini import GeminiAIDriver
from engine.ai.drivers.mock import MockAIDriver
from engine.ai.drivers.openai import OpenAIDriver
from engine.exceptions.handler import MisconfigurationError


class AIManager:
    """Manager and entry point for all AI provider operations."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app
        self._drivers: Dict[str, AIDriver] = {}

    def _get_config(self) -> Dict[str, Any]:
        if self.app:
            try:
                cfg = self.app.make("config")
                return {
                    "default": cfg.get("ai.default", "mock"),
                    "drivers": cfg.get("ai.drivers", {}),
                }
            except Exception:
                pass
        return {"default": "mock", "drivers": {"mock": {"model": "mock-ai-model"}}}

    def driver(self, name: Optional[str] = None) -> AIDriver:
        """Resolve an AI driver instance by name or default."""
        cfg = self._get_config()
        driver_name = name or cfg.get("default", "mock")

        if driver_name in self._drivers:
            return self._drivers[driver_name]

        driver_config = cfg.get("drivers", {}).get(driver_name, {})

        if driver_name == "gemini":
            instance = GeminiAIDriver(driver_config)
        elif driver_name == "openai":
            instance = OpenAIDriver(driver_config)
        elif driver_name == "mock":
            instance = MockAIDriver(driver_config)
        else:
            # Never degrade to the mock: an app configured for a real provider
            # must not receive fabricated answers with no error.
            raise MisconfigurationError(
                "AI_DRIVER_UNKNOWN",
                name=driver_name,
                drivers=", ".join(sorted(cfg.get("drivers", {}))) or "none",
            )

        self._drivers[driver_name] = instance
        return instance

    def set_driver(self, name: str, driver_instance: AIDriver) -> None:
        """Register a custom driver instance (e.g. for tests)."""
        self._drivers[name] = driver_instance

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        driver: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> AIResponse:
        """Send chat messages to the selected or default AI driver."""
        return self.driver(driver).chat(messages=messages, model=model, tools=tools, **kwargs)

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        driver: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text completion from a prompt string."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self.chat(messages=messages, model=model, driver=driver, **kwargs)
        return resp.content

    def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        driver: Optional[str] = None,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate vector embeddings for text(s)."""
        return self.driver(driver).embed(texts=texts, model=model, **kwargs)

    def agent(
        self,
        tools: Optional[List[Any]] = None,
        system_prompt: Optional[str] = None,
        max_steps: int = 10,
        model: Optional[str] = None,
        driver: Optional[str] = None,
    ) -> AIAgent:
        """Create an autonomous AI Agent with tool-calling capabilities."""
        return AIAgent(
            driver=self.driver(driver),
            tools=tools,
            system_prompt=system_prompt,
            max_steps=max_steps,
            model=model,
        )
