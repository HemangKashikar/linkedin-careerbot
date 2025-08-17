import os
import time
import csv
import json
import getpass
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

CONFIG_FILE = "config.json"
CSV_FILE = "linkedin_data.csv"
VECTORDB_DIR = "linkedin_faiss_index"

# ============================
# CONFIG HELPERS
# ============================
def load_config() -> Dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg: Dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def append_to_csv_row(file_path: str, row: Dict):
    file_exists = os.path.exists(file_path)
    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# ============================
# LLM SETUP
# ============================
def build_gemini_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key="",
        temperature=0.3
    )

# ============================
# SCRAPER
# ============================
def scrape_profile(email: str, password: str, profile_url: str) -> str:
    print("🔑 Logging into LinkedIn...")
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)

    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(5)

    print("📄 Visiting profile...")
    driver.get(profile_url)
    time.sleep(5)

    page_text = driver.find_element(By.TAG_NAME, "body").text
    driver.quit()
    return page_text

# ============================
# ANALYSIS + SAVE
# ============================
def extract_json_from_text(text: str) -> Dict:
    """Ensure clean JSON parsing from Gemini response"""
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except Exception:
        return {"raw": text}

def scrape_analyze_and_save(email: str, password: str, profile_url: str) -> str:
    text = scrape_profile(email, password, profile_url)
    llm = build_gemini_llm()

    # Profile analysis prompt
    analysis_prompt = PromptTemplate(
        input_variables=["profile_text"],
        template="""You are analyzing a LinkedIn profile. 

Task:
1. Extract the person's full name (return just the name string).
2. Check if the person has an AWS certification.
3. Provide a confidence score (0–100).
4. Write a short structured JSON summary.

Profile Text:
{profile_text}"""
    ).format(profile_text=text)

    raw = llm.invoke(analysis_prompt)
    parsed = extract_json_from_text(raw.content if hasattr(raw, "content") else str(raw))

    # Build recruiter-friendly summary
    summ_prompt = f"""
You are a concise recruiter assistant. Create a 3-sentence recruiter-friendly summary for this profile using this analysis:
{json.dumps(parsed)}
"""
    summ_resp = llm.invoke(summ_prompt)
    final_summary = summ_resp.content.strip() if hasattr(summ_resp, "content") else str(summ_resp).strip()

    # Compose CSV row
    row = {
        "profile_url": profile_url,
        "name": parsed.get("name", ""),
        "has_aws_cert": parsed.get("has_aws_cert", False),
        "confidence": parsed.get("confidence", 0),
        "analysis_raw": json.dumps(parsed),
        "summary": final_summary
    }
    append_to_csv_row(CSV_FILE, row)

    # Save to FAISS
    doc = Document(
        page_content=final_summary,
        metadata={
            "name": parsed.get("name", "").strip(),
            "url": profile_url,
            "has_aws_cert": parsed.get("has_aws_cert", False),
            "confidence": parsed.get("confidence", 0)
        }
    )
    vs = append_doc_to_faiss(VECTORDB_DIR, doc)
    print(f"✅ Saved profile for '{parsed.get('name','(unknown)')}' to CSV and FAISS.")
    return parsed.get("name", "").strip()

def append_doc_to_faiss(vdb_dir: str, doc: Document):
    embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    if os.path.exists(vdb_dir):
        vs = FAISS.load_local(vdb_dir, embedder, allow_dangerous_deserialization=True)
        vs.add_documents([doc])
    else:
        vs = FAISS.from_documents([doc], embedder)
    vs.save_local(vdb_dir)
    return vs

# ============================
# CHATBOT LOOP
# ============================
def career_chatbot_loop():
    embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    if not os.path.isdir(VECTORDB_DIR) or not os.listdir(VECTORDB_DIR):
        print("⚠️ Vector DB empty. Run the scraper/save flow first.")
        return

    vs = FAISS.load_local(VECTORDB_DIR, embedder, allow_dangerous_deserialization=True)
    llm = build_gemini_llm()

    print("🤖 CareerBot ready. Enter person full name (exact or partial). Type 'exit' to quit.")
    while True:
        person_name = input("Person name> ").strip()
        if person_name.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            break

        found_docs: List[Document] = []
        try:
            candidates = vs.similarity_search(person_name, k=8)
        except Exception:
            candidates = []

        for d in candidates:
            name_meta = (d.metadata.get("name") or "").strip()
            if name_meta and person_name.lower() in name_meta.lower():
                found_docs.append(d)

        if not found_docs:
            print(f"⚠️ No profile found for '{person_name}'.")
            continue

        context = "\n\n".join([d.page_content for d in found_docs[:3]])
        profile_url = found_docs[0].metadata.get("url", "N/A")
        aws_status = found_docs[0].metadata.get("has_aws_cert", False)
        print(f"✅ Found profile: {found_docs[0].metadata.get('name','(unknown)')} — {profile_url} (AWS cert: {aws_status})")

        while True:
            q = input("You> ").strip()
            if q.lower() in ("back", "change", "person"):
                break
            if q.lower() in ("exit", "quit", "bye"):
                print("Goodbye!")
                return

            prompt = f"""
You are a friendly career advisor. Use ONLY the profile summary/context below to answer the user's question.
Profile context:
{context}

User question:
{q}

Also consider if the user already has AWS certification (AWS cert = {aws_status}).
Give actionable, specific suggestions: certifications, courses, skills to add to LinkedIn, and how to reorder their experience to highlight AWS compatibility.
Keep answer concise and practical.
"""
            resp = llm.invoke(prompt)
            answer = resp.content if hasattr(resp, "content") else str(resp)
            print("\nCareerBot:", answer.strip(), "\n")

# ============================
# CLI MAIN
# ============================
def main():
    cfg = load_config()

    if not cfg.get("linkedin_email") or not cfg.get("linkedin_password") or not cfg.get("profile_url"):
        print("Enter LinkedIn credentials and profile URL (saved persistently in config.json):")
        email = input("LinkedIn email: ").strip()
        pwd = getpass.getpass("LinkedIn password: ").strip()
        url = input("Profile URL (optional): ").strip()
        cfg["linkedin_email"] = email
        cfg["linkedin_password"] = pwd
        if url:
            cfg["profile_url"] = url
        save_config(cfg)
    else:
        print("Loaded credentials from config.json")

    while True:
        print("\nOptions:\n 1) Scrape & Save profile now\n 2) Start CareerBot (query saved profiles)\n 3) Update saved config\n 4) Exit")
        choice = input("Choose (1/2/3/4): ").strip()
        if choice == "1":
            profile_url = cfg.get("profile_url") or input("Profile URL: ").strip()
            if profile_url:
                scrape_analyze_and_save(cfg["linkedin_email"], cfg["linkedin_password"], profile_url)
        elif choice == "2":
            career_chatbot_loop()
        elif choice == "3":
            email = input("LinkedIn email: ").strip()
            pwd = getpass.getpass("LinkedIn password: ").strip()
            url = input("Default profile URL (optional): ").strip()
            cfg["linkedin_email"] = email
            cfg["linkedin_password"] = pwd
            if url:
                cfg["profile_url"] = url
            save_config(cfg)
            print("Config updated.")
        elif choice == "4":
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
