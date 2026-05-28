# Already Here Command OS — Developer AI Tools

All tools below are configured to use your existing API keys. Keys live in
`~/.bashrc`, `~/.zshrc`, or your shell profile — never commit them.

---

## Environment Setup (add to ~/.bashrc or ~/.zshrc)

```bash
# Already Here LLC — AI API Keys
export GROQ_API_KEY="your-groq-api-key-here"
export GEMINI_API_KEY="your-gemini-api-key-here"
export OPENROUTER_API_KEY="your-openrouter-api-key-here"
export DEEPSEEK_API_KEY="your-deepseek-api-key-here"  # needs $5 credit top-up

# Get free from:
# Mistral/Codestral: https://console.mistral.ai  → MISTRAL_API_KEY
# Qwen: https://dashscope.aliyuncs.com           → QWEN_API_KEY
```

---

## 1. Aider (CLI pair programmer)

```bash
pip install aider-chat

# Use Groq (free, fast)
aider --model groq/llama-3.3-70b-versatile

# Use Gemini (free)
aider --model gemini/gemini-2.5-flash

# Use GPT-4o-mini via OpenRouter (BYOK)
aider --model openrouter/openai/gpt-4o-mini

# Use local Ollama (zero cost after setup)
aider --model ollama/qwen2.5-coder:7b

# Config file .aider.conf.yml is already in project root — just run:
aider
```

---

## 2. Continue.dev (VS Code Extension)

1. Install: VS Code → Extensions → search **Continue**
2. Config is already at `.continue/config.json` in this repo
3. Replace `$MISTRAL_API_KEY` etc. with your actual keys in the config
4. Best autocomplete: **Codestral** (free at console.mistral.ai)

---

## 3. Gemini CLI

```bash
# Install
npm install -g @google/gemini-cli
# or
pip install google-generativeai

# Set key
export GEMINI_API_KEY="your-gemini-api-key-here"

# Run
gemini  # interactive
gemini -p "explain this codebase"
```

---

## 4. OpenCode

```bash
npm install -g opencode-ai

# Configure with Groq (free)
opencode config set provider groq
opencode config set model llama-3.3-70b-versatile
opencode config set api-key $GROQ_API_KEY

# Or Gemini
opencode config set provider google
opencode config set api-key $GEMINI_API_KEY
```

---

## 5. Cursor IDE (Free + Gemini)

1. Download: https://cursor.sh
2. Settings → Models → Add Model
3. Provider: **Google**, Key: `$GEMINI_API_KEY`, Model: `gemini-2.5-flash`
4. Or: Provider: **OpenAI-Compatible**, Base URL: `https://api.groq.com/openai/v1`
   Key: `$GROQ_API_KEY`, Model: `llama-3.3-70b-versatile`

---

## 6. Ollama (Local — Zero Cost Forever)

```bash
# Install (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull best free code models
ollama pull qwen2.5-coder:7b     # best code model, 4.7GB
ollama pull llama3.2              # fast general model, 2GB
ollama pull phi3.5                # tiny but capable, 2.2GB

# Start server (OpenAI-compatible at localhost:11434)
ollama serve

# Add to Cash AI (in server .env):
# OLLAMA_BASE_URL=http://YOUR_IP:11434
# OLLAMA_MODEL=qwen2.5-coder:7b
```

---

## 7. KoboldCpp (Local — Zero Cost, CPU/GPU)

```bash
# Download from: https://github.com/LostRuins/koboldcpp/releases
# Then run any GGUF model:
./koboldcpp --model path/to/model.gguf --port 5001

# Add to Cash AI (in server .env):
# KOBOLD_BASE_URL=http://YOUR_IP:5001
# KOBOLD_MODEL=koboldcpp
```

---

## 8. Qwen (Alibaba — Free Tier)

```bash
# Get free key: https://dashscope.aliyuncs.com → API Keys
# Add to .env: QWEN_API_KEY=sk-...
# Models: qwen-plus (recommended), qwen-turbo, qwen-max
```

---

## Cash AI Provider Priority (server)

```
1. Groq llama-3.3-70b       ← primary  (free, 30 req/min)
2. Gemini 2.5-flash          ← backup   (free tier)
3. Mistral small             ← backup   (free tier, needs key)
4. Codestral                 ← code     (free tier, needs key)
5. Ollama (local model)      ← local    (zero cost, needs setup)
6. KoboldCpp (local model)   ← local    (zero cost, needs setup)
7. Qwen Plus                 ← cloud    (free tier, needs key)
8. DeepSeek chat             ← cloud    (needs $5 credit)
9. OpenRouter gpt-4o-mini    ← BYOK     (your OpenAI key)
10. OpenRouter gpt-4o        ← BYOK     (your OpenAI key)
11. Gemini 1.5-flash         ← last resort
```
