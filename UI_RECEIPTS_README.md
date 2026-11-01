# VoiceOps UI refresh + verified PDF order receipts

The updated Streamlit app uses the supplied blue/violet, near-black reference artwork and an Oxanium-style futuristic display font, with white text. It preserves `src/core.py`, Groq + RAG, Gnani STT and TTS, and multi-turn sessions.

## Direct replacement into an existing VS Code project

Copy the following files to their exact paths:

- `voiceops_interactive.py` — **replace** the existing Streamlit UI.
- `src/receipt_generator.py` — **add** the verified synthetic PDF order receipt generator.
- `assets/voiceops_background.png` — **add** the user-provided gradient background artwork.
- `tests/test_receipt_generator.py` — **add** optional unit tests.

If using the *full* updated-project ZIP rather than a patch, you can simply extract it into a new directory (then restore your dataset and environment file locally).

Keep the existing `src/core.py`, `.env`, and dataset. Do not commit `.env` or `vendor/` to a public repository.

## Install and run (PowerShell inside VS Code)

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run voiceops_interactive.py
```

Open the displayed local URL (typically http://localhost:8501).

For a clean folder, first create/activate a venv, copy `.env.example` to `.env` and enter your **own** Groq and Gnani keys. The dataset must be extracted to `vendor/Capstone_Project_Dataset_FTTT_2026/`.

## Receipt demo (uses synthetic dataset)

1. Open the **ORDER RECEIPTS** tab.
2. Enter order ID `69520867`.
3. Enter delivery PIN `160017` (part of the synthetic dataset).
4. Inspect the verified item list; optionally filter by product name or SKU.
5. Press **Download order receipt (PDF)**. The PDF includes **all items** in the order.

When testing another order, use the matching synthetic test identity information in the dataset; never use real customer credentials.

## Security and scope

- The receipt tab talks to the **same session-scoped Agent** used by the chat; failed proof attempts remain limited by existing agent rules.
- An order ID alone **cannot** download a receipt. The generator also rejects unverified tool results.
- Uses the verified order's original line-item prices, subtotal, discounts, fees and total.
- Item-name search filters **only the previously verified order**, not all customers' orders. Broader order-history search needs additional authenticated lookup logic.
- This document is a **synthetic order receipt, not an official GST invoice** (no statutory invoice number or tax split in the dataset).
- Human handover is a simulated decision; real ticket creation is disabled in the Streamlit demo.
- If the Gnani key is absent, text-mode chat can still work with a configured LLM, but voice recognition and synthesis require Gnani credentials.

## Tests

Previous capstone: 23 tests. Added: 3 PDF/order receipt tests. Total: **26 tests** passed in the development environment. The voice UI itself has not been visually browser-tested in this environment; run it locally in VS Code to confirm the design and the API integrations.

## NEW: Generate receipts using spoken conversation

The updated VOICE ASSISTANT tab can now handle receipt requests end-to-end:

1. Speak or type **"Download my invoice"**.
2. Say the eight-digit order number. For example, speak each digit of the synthetic test order **69520867**: "six nine five two zero eight six seven".
3. When asked, speak the registered phone's last four digits OR the matching six-digit delivery PIN. The synthetic demo order has delivery PIN **160017**, which you can speak as "one six zero zero one seven".
4. Once the existing Agent verifies the order, a **Download receipt (PDF)** button appears directly under its reply in the conversation tab.
5. Click the button to save the document. Web browsers do not permit arbitrary background file downloads simply because speech was recognized.

The assistant also accepts typed requests and Hindi receipt keywords such as `रसीद` and `बिल`; Gnani speech recognition quality depends on your language selection and account configuration. The original manual ORDER RECEIPTS tab remains an alternative.

The new routing logic lives in `src/voice_receipts.py`; it is deliberately outside `src/core.py` so that the original 96-turn conversation evaluator stays unchanged. Requests and verification happen through the existing Agent; the PDF is only attached after successful server-side verification. The spoken PIN/phone suffix is hidden from the visible chat and redacted from the session's Agent history for receipt flows. Old receipt download buttons are hidden if a session changes to a different order or loses verification.

To install from the **voice-receipts patch**, replace `voiceops_interactive.py`, add `src/voice_receipts.py`, and keep the supplied `src/receipt_generator.py` and `assets/voiceops_background.png`. Install the PDF library if missing:

```powershell
python -m pip install reportlab
python -m pytest -q
python -m streamlit run voiceops_interactive.py
```

For genuine business use, implement real authentication, authorization and audit controls; the capstone's phone suffix/delivery PIN checks and synthetic database are not a production identity service.
