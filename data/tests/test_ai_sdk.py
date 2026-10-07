"""Tests for Craft AI SDK and Agent Orchestrator."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from craft.facades import AI
from craft.ai.contracts import AIResponse, EmbeddingResponse, ToolCall
from craft.ai.drivers.mock import MockAIDriver


def sample_calculator(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


def fetch_user_profile(user_id: int) -> dict:
    """Fetch user profile information."""
    return {"id": user_id, "name": "Alice", "role": "admin"}


class TestAISDK:
    def test_ai_generate_simple(self):
        result = AI.generate("Hello world")
        assert "Mock response for: Hello world" in result

    def test_ai_chat_response(self):
        resp: AIResponse = AI.chat([{"role": "user", "content": "What is 2+2?"}])
        assert resp.content.startswith("Mock response for:")
        assert resp.model == "mock-ai-model"
        assert resp.finish_reason == "stop"

    def test_ai_embed_single_and_batch(self):
        emb_single: EmbeddingResponse = AI.embed("Craft Framework AI")
        assert len(emb_single.vector) == 16
        assert isinstance(emb_single.vector[0], float)

        emb_batch: EmbeddingResponse = AI.embed(["First text", "Second text"])
        assert len(emb_batch.embeddings) == 2
        assert len(emb_batch.embeddings[0]) == 16
        assert len(emb_batch.embeddings[1]) == 16

    def test_ai_agent_direct_answer_without_tools(self):
        agent = AI.agent(tools=[sample_calculator], system_prompt="You are an assistant.")
        result = agent.run("Hello there")
        assert result.success is True
        assert len(result.steps) == 1
        assert "Mock response for: Hello there" in result.final_response

    def test_ai_agent_with_tool_calling(self):
        mock_driver = MockAIDriver()
        # 1. Queue a tool call to sample_calculator
        mock_driver.queue_tool_call("sample_calculator", {"a": 10, "b": 25})
        # 2. Queue final text answer
        mock_driver.queue_response("The answer is 35.")

        agent = AI.agent(tools=[sample_calculator, fetch_user_profile])
        agent.driver = mock_driver

        result = agent.run("Calculate 10 + 25")
        assert result.success is True
        assert len(result.steps) == 2
        assert result.steps[0].tool_outputs["sample_calculator"] == 35
        assert result.final_response == "The answer is 35."


class TestUnknownDriverIsRefused:
    """An unknown driver name fails loudly instead of answering from the mock."""

    def test_chat_with_an_unknown_driver_raises(self):
        from craft.exceptions.handler import MisconfigurationError

        with pytest.raises(MisconfigurationError) as excinfo:
            AI.chat([{"role": "user", "content": "hi"}], driver="not-a-driver")
        assert excinfo.value.code == "AI_DRIVER_UNKNOWN"
