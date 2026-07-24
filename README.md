## Hi there 👋

### jimmy-openai

OpenAI SDK-compatible Python client for [chatjimmy.ai](https://chatjimmy.ai) (Llama 3.1 8B) — chat completions, streaming, models, and tool calling.

```bash
pip install -e .
```

```python
from jimmy import Jimmy  # or: from jimmy import OpenAI

client = Jimmy()
r = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "Hello"}],
)
print(r.choices[0].message.content)
```

See [SDK.md](./SDK.md), `examples/`, and `tests/test_sample_usage.py` for runnable sample usage.

**Browser / CORS:** chatjimmy blocks browser CORS — use [`singlefile/`](./singlefile/) (Cloudflare Worker + browser JS class, or one-file Python proxy).

<!--
**senthil-connektcapital/senthil-connektcapital** is a ✨ _special_ ✨ repository because its `README.md` (this file) appears on your GitHub profile.

Here are some ideas to get you started:

- 🔭 I’m currently working on ...
- 🌱 I’m currently learning ...
- 👯 I’m looking to collaborate on ...
- 🤔 I’m looking for help with ...
- 💬 Ask me about ...
- 📫 How to reach me: ...
- 😄 Pronouns: ...
- ⚡ Fun fact: ...
-->
