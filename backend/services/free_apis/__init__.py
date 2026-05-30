"""Free third-party AI provider clients.

All of these are truly $0/mo with no credit card required:

  - Pollinations.ai      keyless    image, text, audio
  - Hugging Face          free tier  image, text, voice cloning, talking-head, music, video
  - Replicate             trial      diverse open-source models (limited free credits)

Strategy:
  * Pollinations is the always-on fallback (no key, no rate limit observed).
  * Hugging Face Inference API unlocks the higher-quality models once the
    operator drops a free `HUGGINGFACE_API_KEY` into `.env` (free at
    https://huggingface.co/settings/tokens).
  * Replicate is opt-in — many of its models are research-only license.

Every helper returns either bytes (for media) or a structured dict, and
fails soft (returns `None` / raises a typed exception) so the caller can
cascade to the next provider.
"""
