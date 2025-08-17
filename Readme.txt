Got it ✅ — here’s a clean **README.md** draft for the project:

---

# 🚀 LinkedIn Profile Scraper + Career Advisor Chatbot

This project combines **LinkedIn scraping, Gemini LLM analysis, and a FAISS vector database** to create a **career advisor chatbot**.

It can:

* 🔍 Scrape LinkedIn profiles automatically (headless Chrome + Selenium).
* 🤖 Analyze profiles with **Google Gemini** to extract:

  * Person’s **full name**
  * **AWS certification status**
  * **Confidence score (0–100)**
  * Structured JSON summary
* 💾 Persistently save results in:

  * `linkedin_data.csv` (structured records)
  * **FAISS VectorDB** (for retrieval & chatbot)
* 💬 Provide career advice through a chatbot that suggests **certifications, skills, and profile improvements** tailored for AWS-certified roles.

---

## ⚙️ Features

* **LinkedIn scraper** (headless mode with Selenium).
* **Gemini-powered analysis** with structured JSON output.
* **Persistent storage** in both CSV and FAISS.
* **CareerBot**: chatbot that retrieves profiles from FAISS by name and suggests improvements.
* Config saved in `config.json` so credentials only need to be entered once.

---

## 📂 Project Structure

```
├── config.json          # Stores LinkedIn credentials + default profile URL
├── linkedin_data.csv    # CSV database of scraped profiles
├── linkedin_faiss_index/ # FAISS persistent vector store
├── script.py            # Main script (scraper + chatbot)
└── README.md            # Documentation
```

---

## 🔑 Requirements

### Python Packages

Install dependencies with:

```bash
pip install selenium langchain langchain-google-genai langchain-community sentence-transformers faiss-cpu
```

### System Requirements

* **Chrome browser** installed.
* **ChromeDriver** matching your Chrome version (make sure it’s in PATH).
* A valid **Google API key** for Gemini (`GOOGLE_API_KEY`).

---

## ▶️ Usage

### 1. Run the Script

```bash
python script.py
```

### 2. Choose an Option

```
Options:
 1) Scrape & Save profile now
 2) Start CareerBot (query saved profiles)
 3) Update saved config
 4) Exit
```

* **Option 1** → Scrapes a LinkedIn profile, analyzes it with Gemini, saves JSON analysis, AWS cert status, and recruiter summary to CSV + FAISS.
* **Option 2** → Starts **CareerBot**. Enter a person’s name to fetch their profile and chat about improvements.
* **Option 3** → Update LinkedIn login credentials or default profile URL.
* **Option 4** → Exit.

---

## 💬 Example Workflow

1. Run the script → choose **Scrape & Save**.
2. Provide profile URL → the system will scrape + analyze.
3. Data saved in `linkedin_data.csv` and `linkedin_faiss_index/`.
4. Run again → choose **CareerBot**.
5. Enter the person’s name → chatbot gives personalized advice, e.g.:

   * “Add AWS Solutions Architect – Associate to your certifications.”
   * “Highlight cloud migration projects in your experience.”
   * “Consider learning Terraform to improve AWS compatibility.”

---

## 📊 Data Saved

For each profile:

* `name`
* `profile_url`
* `has_aws_cert` (True/False)
* `confidence` (0–100)
* `analysis_raw` (JSON from Gemini)
* `summary` (recruiter-friendly text)

Stored in:

* **CSV** → easy export.
* **FAISS VectorDB** → enables chatbot retrieval.

---

## ⚠️ Notes

* Be careful with LinkedIn scraping — respect rate limits and terms of service.
* Credentials (`config.json`) are stored **locally** only.
* Gemini API costs may apply depending on your usage.

---