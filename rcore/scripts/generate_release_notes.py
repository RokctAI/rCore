# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import requests
import json
import os
from rcore.services.llm_service import get_api_key

def generate_release_notes(commit_log, version_name="vNext"):
    """
    Generates AI-written release notes using Groq (Llama 3) for the provided commit log.
    This function is designed to be called via API.
    
    :param commit_log: String containing the raw git log
    :param version_name: String version identifier
    :return: String containing the Markdown release notes
    """
    if not commit_log:
        return "No changes provided."

    # 1. Get API Key
    api_key = get_api_key("groq")
    if not api_key:
        return "Error: Groq API Key not found in Brain Settings."

    # 2. Call Groq (Llama 3 70B)
    print(f"📝 Asking Brain (Groq 70B) to summarize commits for {version_name}...")
    
    system_prompt = """You are an expert Release Manager. 
    Analyze the following git commit logs and write a high-quality, professional Release Note in Markdown format.
    
    Rules:
    - Group changes logically (Features, Fixes, Chores, Refactors).
    - Ignore trivial updates (typos, README).
    - Use emojis for sections (✨ Features, 🐛 Fixes).
    - Be concise but descriptive.
    - Mention the Version Name in the title.
    - Do NOT include 'Here are the release notes' filler text. Just the markdown.
    """
    
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Version: {version_name}\n\nCommits:\n{commit_log}"}
        ],
        "temperature": 0.5
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        
        ai_response = response.json()
        content = ai_response['choices'][0]['message']['content']
        return content
        
    except Exception as e:
        return f"AI Error: {e}"
