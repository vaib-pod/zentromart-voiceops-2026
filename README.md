# ZentroMart VoiceOps --- VoiceOps 2026 Capstone

**A document-grounded customer-support assistant with multi-turn order
workflows, Gnani.ai speech input/output, and downloadable PDF order
receipts.**

> **Public GitHub repository:** Add your repository URL here before
> submission.

## Project overview

ZentroMart VoiceOps is a prototype support assistant for the fictional
Indian online retailer ZentroMart. It answers customer questions using
the supplied company knowledge base, supports follow-up conversations,
protects synthetic order details behind a verification step, and accepts
voice input through Gnani.ai.

The project was developed in four stages:

1.  **Prompt-only baseline** --- a hosted LLM answers without retrieval
    or order tools.
2.  **Retrieval-Augmented Generation (RAG)** --- relevant policy and
    help-document sections are retrieved and supplied as context to the
    LLM.
3.  **Multi-turn support agent** --- a session-aware controller handles
    follow-ups, synthetic order lookup, verification and escalation
    decisions.
4.  **Voice integration** --- Gnani.ai speech-to-text (STT) transcribes
    customer audio and text-to-speech (TTS) generates the spoken reply.

Additional work includes a Streamlit chat/voice interface and a verified
PDF order-receipt download flow.

## Main features

-   Word- and character-level TF-IDF retrieval with policy-aware
    ranking.
-   Source-section evidence returned with RAG responses.
-   Prompt-only baseline for comparison with RAG.
-   Multi-turn conversation state and guarded synthetic order lookup.
-   Verification before displaying order-specific information.
-   Gnani.ai STT/TTS integration.
-   Folder-based WAV batch processing through `run.py`.
-   Streamlit interface with text/voice interaction.
-   PDF order receipt generation after successful order verification.

**Important:** This is an educational prototype using synthetic records
and mock support tools. It is not a production customer-authentication
or ticketing system. The generated order receipt is an educational
receipt, not a GST tax invoice or proof of payment.

## Repository structure

``` text
zentromart-voiceops-2026/
├── assets/                     # UI background and visual assets
├── demo/
│   └── demo_script.md          # Two-minute demo outline
├── reports/                    # Evaluation outputs and supporting reports
├── scripts/
│   ├── build_index.py
│   ├── evaluate.py
│   ├── evaluate_stage3_offline.py
│   ├── test_gnani_stt.py
│   ├── test_gnani_tts.py
│   └── voice_agent.py
├── src/
│   ├── core.py                 # LLM, retrieval and support-agent logic
│   ├── voice.py                # Gnani batch voice adapter
│   └── ...                     # Other supporting modules
├── tests/
├── .env.example
├── .gitignore
├── ARCHITECTURE.md
├── requirements.txt
├── run.py                      # CLI and folder-based audio runner
└── voiceops_interactive.py     # Streamlit application
```

The supplied dataset is intentionally kept outside the public
repository. It must be downloaded separately and extracted into the
local `vendor/` directory.

## Requirements

-   Windows 10/11 (the commands below use PowerShell; adapt paths for
    other operating systems).
-   Python 3.10 or newer; Python 3.11 is recommended.
-   Git.
-   A Groq API key for hosted LLM responses.
-   A Gnani.ai API key for live STT/TTS.
-   The official `Capstone_Project_Dataset_FTTT_2026.zip` supplied with
    the capstone brief.

## Setup on Windows (VS Code)

### 1. Clone the repository

Open a VS Code terminal (PowerShell) and run:

``` powershell
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Replace the URL and folder name with your actual public GitHub
repository details.

### 2. Create and activate a virtual environment

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks activation for this terminal, run:

``` powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

``` powershell
python -m pip install -r requirements.txt
```

### 4. Download and extract the dataset

Download the original, unmodified
`Capstone_Project_Dataset_FTTT_2026.zip` from the official capstone
course source. Do not use a modified dataset.

Create the local dataset directory:

``` powershell
New-Item -ItemType Directory -Force .\vendor | Out-Null
```

If the ZIP is in your Downloads folder, extract it with:

``` powershell
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\Capstone_Project_Dataset_FTTT_2026.zip" -DestinationPath ".\vendor" -Force
```

The expected path is:

``` text
vendor/
└── Capstone_Project_Dataset_FTTT_2026/
    ├── kb/
    ├── data/
    ├── practice/
    ├── tools/
    └── validate_dataset.py
```

Check that the extraction succeeded:

``` powershell
Test-Path .\vendor\Capstone_Project_Dataset_FTTT_2026\kb
Test-Path .\vendor\Capstone_Project_Dataset_FTTT_2026\validate_dataset.py
```

Both commands should return `True`.

If the dataset is stored elsewhere, set `VOICEOPS_DATASET_DIR` to the
extracted dataset-folder path in `.env`.

### 5. Configure API keys

Create your local environment file:

``` powershell
Copy-Item .env.example .env
```

Open `.env` and enter your own credentials:

``` env
GROQ_API_KEY=your_groq_api_key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
GNANI_API_KEY=your_gnani_api_key
```

Do not commit `.env`, share API keys, or paste them into issue reports.
The Streamlit application loads `.env` automatically.

For command-line scripts such as `run.py` and `scripts/evaluate.py`,
load the values into the current PowerShell session before running them:

``` powershell
Get-Content .env | Where-Object { $_ -match '^\s*[^#\s][^=]*=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
}
$env:PYTHONUTF8 = '1'
```

Repeat this step whenever you open a new terminal for CLI use.

## Run the application

From the repository root, with the virtual environment activated and the
dataset extracted:

``` powershell
python -m streamlit run voiceops_interactive.py
```

Streamlit will display a local address, usually `http://localhost:8501`.
Open it in your browser.

The interface supports text and voice interaction. The receipt workflow
requires an order ID and successful synthetic verification before order
details or a receipt are shown. Ticket creation is disabled in the
interactive demonstration.

## Command-line usage

### Prompt-only baseline

``` powershell
python run.py --baseline --question "What is your return policy?"
```

### RAG-backed support answer

``` powershell
python run.py --question "What is the return window for electronics?"
```

The CLI uses the configured LLM credentials. The RAG path also requires
the dataset.

## Folder-based voice batch run

The project includes a batch runner in `run.py`. It accepts a folder of
WAV recordings, processes each recording through Gnani STT, the support
agent and Gnani TTS, and writes the result files to an output directory.

### Audio input requirements

-   WAV format only.
-   Uncompressed 16-bit PCM.
-   One or two audio channels.
-   Maximum duration: 60 seconds per file.
-   Maximum file size: 12 MB.
-   The batch adapter currently requests STT language `en-IN`.

Create an input folder and place the WAV recordings directly inside it:

``` powershell
New-Item -ItemType Directory -Force .\sample_audio | Out-Null
```

Run the batch processor:

``` powershell
python run.py --input-dir .\sample_audio --output-dir .\sample_outputs
```

### Batch output

For each input file named `customer1.wav`, the output directory
contains:

``` text
sample_outputs/
├── customer1_reply.wav
├── customer1_result.json
└── results.json
```

-   `*_reply.wav` --- generated Gnani TTS audio.
-   `*_result.json` --- input filename, customer transcript, agent reply
    text, retrieved evidence chunks, audio status and output-audio path.
-   `results.json` --- combined status summary for all processed files.

The batch runner processes files directly inside the input folder; it
does not recursively scan subfolders. Failed files are recorded in the
JSON results so that the run can be inspected.

## Tests and evaluation

Run the automated tests:

``` powershell
python -m pytest -q
```

Run the offline multi-turn decision replay:

``` powershell
python scripts/evaluate_stage3_offline.py
```

Build the retrieval manifest:

``` powershell
python scripts/build_index.py
```

Run the full practice evaluation only when you intend to make live Groq
API calls:

``` powershell
python scripts/evaluate.py
```

The full evaluation sends requests to the configured LLM provider and
may consume API quota or encounter provider rate limits. Previously
recorded evaluation outputs are stored in `reports/`.

## Recorded development results

The saved project evaluation records report:

  Measurement                                                      Recorded result
  ------------------------------------------- ------------------------------------
  Pytest                                                            23 / 23 passed
  Offline multi-turn decision-label matches                                96 / 96
  Live baseline requests                                                   51 / 52
  Live RAG requests                                                        52 / 52
  Mean gold-section Recall@5                    64.89% across 47 evaluable prompts

Interpret these results carefully:

-   `96/96` measures offline decision-label agreement using a RAG stub;
    it is not live dialogue or answer-quality accuracy.
-   `64.89% Recall@5` measures retrieval coverage of expected
    knowledge-base sections; it is not answer accuracy.
-   Generated answer accuracy was not independently adjudicated.
-   Live Gnani STT/TTS was tested during development. The API
    credentials and local audio recordings are not included in this
    repository.

See `reports/` for the saved evaluation artefacts and `ARCHITECTURE.md`
for the system diagram and trust boundaries.

## Demo

`demo/demo_script.md` contains the planned two-minute walkthrough. Add
the actual recording as `demo/demo.mp4` before final submission. The
video should show:

1.  A policy question answered using retrieved company documents.
2.  A contextual follow-up in the same conversation.
3.  A handover or an explicit "I don't know" response.
4.  A voice interaction.

Do not describe the demo video as complete until the recording has been
created and checked.

## Security and data handling

-   Never commit `.env`, API keys, or other credentials.
-   Do not upload the supplied dataset archive or the extracted
    `vendor/` directory.
-   Keep generated mock ticket records and private test recordings out
    of the repository.
-   The dataset and order-verification tools are synthetic and must not
    be used with real customer information.
-   Audio and text sent to Groq or Gnani are processed by those external
    services when live API features are used.

## Known limitations

-   The system is a capstone prototype, not a production
    customer-support deployment.
-   Order verification and ticket actions use synthetic/mock data.
-   Session state is local to the running process/session.
-   Ticket creation is disabled in the Streamlit demonstration.
-   Retrieval can miss relevant sections, and generated answer accuracy
    has not been independently graded.
-   The current batch audio adapter accepts validated WAV input and uses
    the `en-IN` STT setting.

## License

Add a license only if you have permission to choose one and the capstone
rules allow it. The supplied synthetic dataset and course materials
remain subject to their original terms.
