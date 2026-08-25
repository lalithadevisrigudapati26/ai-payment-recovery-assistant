from google import genai
import json
import pandas as pd
import time
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Paste your API key between the quotes below

def analyze_transaction(customer_name, amount, failure_reason_raw):
    prompt = f"""
    A customer named {customer_name} tried to pay Rs.{amount} but the payment failed.
    The system logged the failure reason as: "{failure_reason_raw}"

    Do two things:
    1. Explain in one simple sentence why this payment likely failed (in plain English, not technical jargon).
    2. Write a short, friendly recovery message (2-3 sentences) to send this customer, encouraging them to try the payment again. Do not sound pushy.

    Respond ONLY in this exact JSON format, nothing else:
    {{
        "reason_explained": "...",
        "recovery_message": "..."
    }}
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    result = json.loads(text)
    return result


# Load all the failed transactions
df = pd.read_csv("failed_transactions.csv")

results = []

for index, row in df.iterrows():
    print(f"Analyzing transaction {index + 1} of {len(df)}: {row['customer_name']}...")
    
    attempts = 0
    success = False
    while attempts < 3 and not success:
        try:
            result = analyze_transaction(row['customer_name'], row['amount'], row['failure_reason_raw'])
            success = True
        except Exception as e:
            attempts += 1
            print(f"  Attempt {attempts} failed ({e}). Retrying in 5 seconds...")
            time.sleep(5)
    
    if not success:
        print(f"  Skipping {row['customer_name']} after 3 failed attempts.")
        continue
    
    results.append({
        "customer_name": row['customer_name'],
        "email": row['email'],
        "amount": row['amount'],
        "failure_reason_raw": row['failure_reason_raw'],
        "reason_explained": result['reason_explained'],
        "recovery_message": result['recovery_message']
    })
    
    time.sleep(2)

output_df = pd.DataFrame(results)
output_df.to_csv("recovery_results.csv", index=False)

print("\nDone! All results saved to recovery_results.csv")
print(f"Total transactions processed: {len(results)}")