
# 📘 Pythonic RAG Assignment — Question Answers

This document contains my responses to the reflection questions from the Pythonic RAG Assignment notebook.

---
## ❓ Question #1

### 1. Is there any way to modify this dimension?

Yes. OpenAI’s embedding models (like `text-embedding-3-small`) allow you to specify a custom output dimension using the `dimensions` parameter in the API call. This lets you reduce the default dimension (1536 for `text-embedding-3-small`) to a smaller size that better fits your compute, memory, or storage constraints.

Example:
```python
response = client.embeddings.create(
  input="Some text",
  model="text-embedding-3-small",
  dimensions=256
)
assert len(response.data[0].embedding) == 256
```
---

### 2. What technique does OpenAI use to achieve this?

OpenAI uses **Matryoshka Representation Learning (MRL)** — a method that trains embeddings in a coarse-to-fine fashion. The most important information is stored in the earliest dimensions, allowing developers to safely truncate the vector (e.g. to 256 dimensions) without significant performance loss.

This makes it possible to adjust embedding size dynamically while preserving semantic richness, enabling trade-offs between accuracy and resource usage.

---

## ❓ Question #2
#### What are the benefits of using an async approach to collecting our embeddings?

Using an async approach to collect embeddings offers significant performance gains, especially when working with I/O-bound operations such as API calls.

In this benchmark:
```
Sync time:  1.0741s  
Async time: 0.6136s
```
The async version is noticeably faster because it does not wait for each request to complete sequentially. Instead, it sends multiple embedding requests concurrently and waits for them together, reducing idle time spent waiting on the network. In contrast, a synchronous approach sends one request, waits for the response, then sends the next — leading to slower total execution.

The key benefits of async include:
- Improved speed: Asynchronous execution parallelizes I/O tasks like API calls.
- Better resource utilization: Async keeps the CPU free while waiting for network responses.
- Scales better: Especially helpful when embedding many texts or making batched requests.

---

### ❓Question #3:  
**When calling the OpenAI API – are there any ways we can achieve more reproducible outputs?**

Yes. To make outputs more reproducible when calling the OpenAI API, you can use the `seed` parameter.

1. **Use the `seed` parameter**  
   Add a fixed integer seed to your API request. This helps the model generate the same output given the same input and parameters.

2. **Keep all other parameters constant**  
   Ensure that parameters like `model`, `messages`, `temperature`, `top_p`, `max_tokens`, etc., remain exactly the same.

3. **Monitor `system_fingerprint` in the response**  
   This value identifies the backend model version. If it changes, results may vary even with the same seed.

> ⚠️ Reproducibility is best-effort and may not be guaranteed in all cases.

**Example:**

```python
import openai

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Tell me a joke"}],
    temperature=0.7,
    top_p=1.0,
    max_tokens=100,
    seed=42
)

print(response['choices'][0]['message']['content'])
print("System fingerprint:", response.get('system_fingerprint'))
```

Reference: https://platform.openai.com/docs/advanced-usage/reproducible-outputs

---
#### ❓ Question #4:

**What prompting strategies could you use to make the LLM have a more thoughtful, detailed response?**

✅ A powerful strategy is called **"chain‑of‑thought prompting."**  
This technique encourages the model to articulate its reasoning step by step before giving the final answer, which often yields more transparent, in‑depth responses.

---

**Example using chain‑of‑thought prompting:**

```markdown
You are an expert in medieval history.

**Question:** Why did the feudal system become dominant in Europe during the Middle Ages?

**Please reason step by step before giving your final answer.**
```

➡️ The model responds by laying out its reasoning chain, showing intermediate steps (like weak central authority, land-for-service arrangements, protection needs), and then concludes with a comprehensive summary.

---

### Why it works:
- Encourages the LLM to **decompose complex problems**.
- Helps avoid **oversimplified or surface-level answers**.
- Makes the thought process **transparent and logical**, useful for validation or teaching.

---

**In short:**  
Use **chain‑of‑thought prompting** to prompt the model to *"think out loud"*—step by step—before delivering the final answer.