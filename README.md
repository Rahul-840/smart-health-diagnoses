# Smart Health Diagnoses

A college-ready medical report analyzer with PDF upload, value extraction, dashboard, diet guidance, recommendations, report history, health tracking, and report-based chatbot support.

## Run locally

```bash
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

Add your OpenRouter key in `.env` only if you want cloud AI summary/chat support:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

The app also works without an API key in local rule-based mode.

## Streamlit Cloud

1. Upload source files to GitHub.
2. Do not upload `.env`, `.db`, or `.health_session.json`.
3. Add this in Streamlit Cloud secrets if using OpenRouter:

```toml
OPENROUTER_API_KEY = "your_openrouter_api_key_here"
```

## Test

Use a text-based CBC/lipid/thyroid PDF. For the sample CBC report, expected key outputs:

- Platelets: Normal when `3.5 lakhs/cumm` appears
- Lymphocytes: Low if value is 18%
- Monocytes: Low if value is 1%
- MCHC: High if value is 35.7%

This app helps explain reports in simple language and does not replace a certified doctor.
