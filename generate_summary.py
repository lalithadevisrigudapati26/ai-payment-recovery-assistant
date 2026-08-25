from google import genai
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

df = pd.read_csv("recovery_results.csv")

# Build a short data summary to send to the AI
reason_breakdown = df["failure_reason_raw"].value_counts().to_dict()
total_amount = df["amount"].sum()
total_count = len(df)

prompt = f"""
You are analyzing payment failure data for a business.

Total failed transactions: {total_count}
Total revenue at risk: Rs.{total_amount}
Breakdown of failure reasons: {reason_breakdown}

Write ONE short, insightful sentence (max 30 words) that a business owner would find useful,
highlighting the biggest opportunity or pattern. Be specific and actionable, not generic.
Respond with ONLY the sentence, nothing else.
"""

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=prompt
)

summary = response.text.strip()

# Save it to a small text file
with open("business_summary.txt", "w") as f:
    f.write(summary)

print("Summary generated:")
print(summary)