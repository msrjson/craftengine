# Craft AI SDK

Craft Engine includes a provider-agnostic, unified **AI SDK** and autonomous **Agent Orchestrator**.

## 🚀 Basic Usage

```python
from craft.facades import AI

# 1. Quick text generation
text = AI.generate("Explain asynchronous event loops in Python.")

# 2. Multi-turn Chat
response = AI.chat([
    {"role": "system", "content": "You are a senior database architect."},
    {"role": "user", "content": "What is the benefit of pgvector?"}
], model="gemini-2.0-flash")

print(response.content)
```

---

## 🤖 Autonomous Agents & Tool-Calling

Create autonomous agents that reason and execute multi-step tools dynamically:

```python
from craft.facades import AI

def calculate_shipping(weight_kg: float, country: str) -> dict:
    """Calculate international shipping rates."""
    rate = 15.0 + (weight_kg * 4.5)
    return {"country": country, "rate": rate}

agent = AI.agent(
    tools=[calculate_shipping],
    system_prompt="You are an e-commerce sales assistant with shipping calculation tools."
)

result = agent.run("How much to ship a 5kg package to Brazil?")
print(result.final_response)
```

---

## 🔍 Vector Embeddings

Generate vector representations for semantic search and classification:

```python
# Single text embedding
emb = AI.embed("Semantic search query")
vector = emb.vector # 16 or 768/1536 dimension float list

# Batch embeddings
batch = AI.embed(["Document 1", "Document 2"])
```
