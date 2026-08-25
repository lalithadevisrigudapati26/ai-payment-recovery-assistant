import pandas as pd

df = pd.read_csv("failed_transactions.csv")

print("Here's a preview of your data:")
print(df.head())

total_transactions = len(df)
total_amount_lost = df["amount"].sum()

print("\n--- Summary ---")
print(f"Total failed transactions: {total_transactions}")
print(f"Total revenue lost: Rs.{total_amount_lost}")

print("\nFailures by reason:")
print(df["failure_reason_raw"].value_counts())