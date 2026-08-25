import streamlit as st
import pandas as pd
import os
import json
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Payment Recovery Assistant", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: #1B2A4A; }

section[data-testid="stSidebar"] { background-color: #F4F6FA; border-right: 1px solid #E2E6ED; }

div[data-testid="stMetric"] {
    background-color: #FFFFFF; border: 1px solid #E2E6ED; border-left: 4px solid #0F9D8C;
    border-radius: 10px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(27,42,74,0.06);
}
div[data-testid="stMetricLabel"] { color: #5B6B8C; }
div[data-testid="stMetricValue"] { color: #1B2A4A; }
div[data-testid="stExpander"] { border: 1px solid #E2E6ED; border-radius: 10px; transition: border-color 0.2s ease; }
div[data-testid="stExpander"]:hover { border-color: #0F9D8C; }

.stButton button, .stDownloadButton button {
    background-color: #1B2A4A; color: white; border-radius: 8px; border: none; font-weight: 500;
}
.stButton button:hover, .stDownloadButton button:hover { background-color: #0F9D8C; color: white; }

div[data-testid="stAlert"] { border-radius: 10px; }

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
.hero-card { animation: fadeInUp 0.5s ease-out; }
.txn-card {
    border: 1px solid #E2E6ED; border-left-width: 5px; border-left-style: solid;
    border-radius: 12px; padding: 18px 22px; margin-bottom: 16px; background-color: white;
    box-shadow: 0 1px 4px rgba(27,42,74,0.06); transition: transform 0.18s ease, box-shadow 0.18s ease;
    animation: fadeInUp 0.4s ease-out;
}
.txn-card:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(27,42,74,0.14); border-left-width: 6px; }
.priority-pill { display: inline-block; transition: transform 0.15s ease; }
.txn-card:hover .priority-pill { transform: scale(1.06); }
.recovery-box { transition: background-color 0.18s ease; }
.txn-card:hover .recovery-box { background-color: #EAF2FF; }
.tag-pill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:0.72rem; font-weight:600; margin-right:6px; }

section[data-testid="stSidebar"] div[data-testid="stFileUploaderDropzone"] { transition: border-color 0.2s ease; }
section[data-testid="stSidebar"] div[data-testid="stFileUploaderDropzone"]:hover { border-color: #0F9D8C !important; }
</style>
""", unsafe_allow_html=True)

st.title("💳 AI Payment Recovery Assistant")
st.markdown("Automatically explains why payments failed and drafts personalized recovery messages.")

if os.path.exists("business_summary.txt"):
    with open("business_summary.txt", "r") as f:
        summary_text = f.read()
    st.success(f"💡 **Key Insight:** {summary_text}")


# ---------- CORE LOGIC FUNCTIONS ----------

def analyze_transaction(client, customer_name, amount, failure_reason_raw):
    """AI-personalized analysis - used only for High priority transactions."""
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
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def generate_template_message(customer_name, amount, failure_reason_raw):
    """Free, rule-based fallback - used for Medium/Low priority to save AI cost."""
    reason_map = {
        "timeout": "the payment request timed out before it could complete",
        "session_expired": "the payment session expired before you finished",
        "otp_failed": "the OTP verification could not be completed in time",
        "insufficient_funds": "there were insufficient funds available at the time",
        "card_declined": "the card issuer declined the transaction",
    }
    reason_text = reason_map.get(failure_reason_raw, "a technical issue occurred during payment")
    return {
        "reason_explained": f"Your payment likely failed because {reason_text}.",
        "recovery_message": f"Hi {customer_name}, your payment of Rs.{amount} didn't go through. Please try again whenever convenient."
    }


def get_priority(row):
    score = 0
    if row["amount"] >= 5000:
        score += 3
    elif row["amount"] >= 1500:
        score += 2
    else:
        score += 1

    easy = ["timeout", "session_expired", "otp_failed"]
    hard = ["insufficient_funds"]
    if row["failure_reason_raw"] in easy:
        score += 3
    elif row["failure_reason_raw"] in hard:
        score += 1
    else:
        score += 2

    if score >= 5:
        return "🔴 High"
    elif score >= 3:
        return "🟡 Medium"
    else:
        return "🟢 Low"


def get_recovery_likelihood(failure_reason_raw):
    """Rule-based estimate of how likely this type of failure is to be recovered."""
    mapping = {
        "timeout": 78,
        "session_expired": 74,
        "otp_failed": 70,
        "card_declined": 45,
        "insufficient_funds": 32,
    }
    return mapping.get(failure_reason_raw, 50)


def get_recommended_channel(priority):
    """Mirrors Razorpay's real multichannel approach: WhatsApp, Email, SMS."""
    if priority == "🔴 High":
        return "📱 WhatsApp"
    elif priority == "🟡 Medium":
        return "✉️ Email"
    else:
        return "💬 SMS"


# ---------- SIDEBAR: DATA SOURCE ----------
st.sidebar.header("📁 Data Source")
mode = st.sidebar.radio("Choose input type:", ["Use sample results (instant)", "Upload raw CSV and analyze with AI"])

MAX_ROWS = 15
df = None

if mode == "Upload raw CSV and analyze with AI":

    with st.sidebar.expander("ℹ️ How to prepare your file"):
        st.markdown("""
        1. Click **Download Sample Template** below
        2. Open it in Excel or Google Sheets
        3. Replace the example row with your real customer data
        4. Save the file, then upload it above
        """)

        sample_template = pd.DataFrame({
            "Customer Name": ["Example Customer"],
            "Amount": [1000],
            "Reason": ["insufficient_funds"]
        })

        st.download_button(
            "📄 Download Sample Template",
            data=sample_template.to_csv(index=False),
            file_name="sample_template.csv",
            mime="text/csv"
        )

    raw_file = st.sidebar.file_uploader("Upload your file", type=["csv"])

    if raw_file is not None:
        raw_df = pd.read_csv(raw_file)

        column_map = {"Customer Name": "customer_name", "Amount": "amount", "Reason": "failure_reason_raw"}
        raw_df = raw_df.rename(columns=column_map)

        required = {"customer_name", "amount", "failure_reason_raw"}
        if not required.issubset(raw_df.columns):
            st.error("Your file is missing required columns. Please use the sample template.")
            st.stop()

        if len(raw_df) > MAX_ROWS:
            st.warning(f"To stay within free AI usage limits, only the first {MAX_ROWS} rows will be analyzed.")
            raw_df = raw_df.head(MAX_ROWS)

        # Compute priority BEFORE deciding AI vs template - this is the tiered strategy
        raw_df["priority"] = raw_df.apply(get_priority, axis=1)

        if st.sidebar.button("🚀 Analyze with AI"):
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            results = []
            progress = st.progress(0, text="Starting analysis...")

            for i, row in raw_df.iterrows():
                use_ai = row["priority"] == "🔴 High"
                progress.progress(
                    (i + 1) / len(raw_df),
                    text=f"{'AI analyzing' if use_ai else 'Templating'} {row['customer_name']}..."
                )

                if use_ai:
                    try:
                        result = analyze_transaction(client, row["customer_name"], row["amount"], row["failure_reason_raw"])
                        message_type = "🤖 AI-Personalized"
                    except Exception as e:
                        st.warning(f"AI failed for {row['customer_name']}, using template instead ({e})")
                        result = generate_template_message(row["customer_name"], row["amount"], row["failure_reason_raw"])
                        message_type = "📋 Template"
                    time.sleep(1)
                else:
                    result = generate_template_message(row["customer_name"], row["amount"], row["failure_reason_raw"])
                    message_type = "📋 Template"

                results.append({
                    "customer_name": row["customer_name"],
                    "amount": row["amount"],
                    "failure_reason_raw": row["failure_reason_raw"],
                    "reason_explained": result["reason_explained"],
                    "recovery_message": result["recovery_message"],
                    "message_type": message_type
                })

            progress.empty()
            df = pd.DataFrame(results)
            st.session_state["analyzed_df"] = df
            ai_used = len(df[df["message_type"] == "🤖 AI-Personalized"])
            st.success(f"Analyzed {len(df)} transactions ({ai_used} AI-personalized, {len(df) - ai_used} templated).")

    if "analyzed_df" in st.session_state:
        df = st.session_state["analyzed_df"]

else:
    if not os.path.exists("recovery_results.csv"):
        st.error("Sample results not found. Please generate recovery_results.csv first.")
        st.stop()
    df = pd.read_csv("recovery_results.csv")

if df is None or len(df) == 0:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px; color:#5B6B8C;">
        <div style="font-size:2.5rem; margin-bottom:12px;">💳</div>
        <div style="font-family:'Space Grotesk',sans-serif; font-size:1.3rem; color:#1B2A4A; font-weight:700; margin-bottom:8px;">
            No transactions analyzed yet
        </div>
        <div>Upload your failed payments file and click <b>Analyze with AI</b> in the sidebar to see recovery opportunities here.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ---------- DERIVED COLUMNS (works for both sample data and fresh uploads) ----------
if "priority" not in df.columns:
    df["priority"] = df.apply(get_priority, axis=1)
if "message_type" not in df.columns:
    df["message_type"] = "🤖 AI-Personalized"  # sample data was fully AI-analyzed

df["recovery_likelihood"] = df["failure_reason_raw"].apply(get_recovery_likelihood)
df["recommended_channel"] = df["priority"].apply(get_recommended_channel)
df = df.sort_values(by="amount", ascending=False)

# ---------- FILTERS ----------
st.sidebar.header("🔍 Filters")
priority_filter = st.sidebar.multiselect(
    "Priority", options=["🔴 High", "🟡 Medium", "🟢 Low"], default=["🔴 High", "🟡 Medium", "🟢 Low"]
)
search_name = st.sidebar.text_input("Search customer name")

filtered_df = df[df["priority"].isin(priority_filter)]
if search_name:
    filtered_df = filtered_df[filtered_df["customer_name"].str.contains(search_name, case=False, na=False)]

# ---------- HERO BANNER ----------
high_count = len(filtered_df[filtered_df["priority"] == "🔴 High"])
expected_recovered = (filtered_df["amount"] * filtered_df["recovery_likelihood"] / 100).sum()

st.markdown(f"""
<div class="hero-card" style="background: linear-gradient(135deg, #1B2A4A 0%, #10203A 100%);
            border-radius:16px; padding:32px 36px; margin-bottom:24px; color:white;">
    <div style="font-size:0.85rem; color:#9DB0D4; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">
        Total recoverable revenue
    </div>
    <div style="font-family:'Space Grotesk',sans-serif; font-size:2.6rem; font-weight:700; color:#4FE0C7;">
        Rs.{filtered_df['amount'].sum():,.0f}
    </div>
    <div style="display:flex; gap:32px; margin-top:18px; flex-wrap:wrap;">
        <div>
            <div style="font-size:1.4rem; font-weight:700;">{len(filtered_df)}</div>
            <div style="font-size:0.8rem; color:#9DB0D4;">Failed transactions</div>
        </div>
        <div>
            <div style="font-size:1.4rem; font-weight:700; color:#FF8A8A;">{high_count}</div>
            <div style="font-size:0.8rem; color:#9DB0D4;">High priority, act first</div>
        </div>
        <div>
            <div style="font-size:1.4rem; font-weight:700; color:#4FE0C7;">Rs.{expected_recovered:,.0f}</div>
            <div style="font-size:0.8rem; color:#9DB0D4;">Expected recovery (est.)</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.download_button(
    "📥 Download Full Report (CSV)",
    data=filtered_df.to_csv(index=False),
    file_name="recovery_report.csv",
    mime="text/csv"
)

st.divider()

# ---------- ROI CALCULATOR ----------
st.markdown("<h3 style='margin-bottom:2px;'>💰 Cost vs. Recovery (ROI estimate)</h3>", unsafe_allow_html=True)
st.caption("Illustrative estimate: AI is used selectively (High priority only) to control cost at scale")

COST_PER_AI_CALL_INR = 0.05  # rough illustrative estimate for a small LLM call

ai_count = len(filtered_df[filtered_df["message_type"] == "🤖 AI-Personalized"])
template_count = len(filtered_df) - ai_count
estimated_ai_cost = ai_count * COST_PER_AI_CALL_INR
roi_multiple = (expected_recovered / estimated_ai_cost) if estimated_ai_cost > 0 else 0

r1, r2, r3 = st.columns(3)
r1.metric("AI-personalized messages", ai_count)
r2.metric("Estimated AI cost", f"Rs.{estimated_ai_cost:.2f}")
r3.metric("Estimated ROI multiple", f"{roi_multiple:,.0f}x" if estimated_ai_cost > 0 else "—")

st.caption(f"{template_count} lower-priority transactions used free rule-based templates instead of AI, keeping cost low at scale.")

st.divider()

# ---------- CHARTS ----------
st.markdown("<h3 style='margin-bottom:2px;'>📊 Where the money is going</h3>", unsafe_allow_html=True)
st.caption("Understand which failure types cost you the most")

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Revenue Lost by Failure Reason**")
    st.bar_chart(filtered_df.groupby("failure_reason_raw")["amount"].sum().sort_values(ascending=False))
with c2:
    st.markdown("**Number of Failures by Reason**")
    st.bar_chart(filtered_df["failure_reason_raw"].value_counts())

st.divider()

# ---------- TRANSACTION DETAILS ----------
st.subheader("Recovery Details")

priority_colors = {
    "🔴 High": ("#E5484D", "#FDEEEE"),
    "🟡 Medium": ("#B8710A", "#FEF3E2"),
    "🟢 Low": ("#0F9D8C", "#E7F7F4")
}
priority_labels = {"🔴 High": "High priority", "🟡 Medium": "Medium priority", "🟢 Low": "Low priority"}

if len(filtered_df) == 0:
    st.markdown("""
    <div style="text-align:center; padding:40px 20px; color:#5B6B8C;">
        <b>No transactions match your filters.</b><br>Try adjusting the priority filter or clearing your search.
    </div>
    """, unsafe_allow_html=True)

for _, row in filtered_df.iterrows():
    text_color, bg_color = priority_colors.get(row["priority"], ("#5B6B8C", "#F4F6FA"))
    label = priority_labels.get(row["priority"], row["priority"])

    st.markdown(f"""
    <div class="txn-card" style="border-left-color:{text_color};">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.05rem; color:#1B2A4A;">
                {row['customer_name']}
            </span>
            <span class="priority-pill" style="background-color:{bg_color}; color:{text_color}; padding:3px 12px;
                         border-radius:999px; font-size:0.75rem; font-weight:600;">
                {label}
            </span>
        </div>
        <div style="color:#5B6B8C; font-size:0.85rem; margin-bottom:8px;">
            Rs.{row['amount']:,} &nbsp;•&nbsp; logged as "{row['failure_reason_raw']}"
        </div>
        <div style="margin-bottom:10px;">
            <span class="tag-pill" style="background-color:#EAF2FF; color:#1B2A4A;">{row['recommended_channel']}</span>
            <span class="tag-pill" style="background-color:#F4F6FA; color:#5B6B8C;">{row['message_type']}</span>
            <span class="tag-pill" style="background-color:#E7F7F4; color:#0F9D8C;">{row['recovery_likelihood']}% likely to recover</span>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1.6])
    with col1:
        st.markdown(f"<div style='color:#1B2A4A;'><b>Why it failed</b><br>{row['reason_explained']}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="recovery-box" style="background-color:#F4F6FA; border-radius:8px; padding:10px 14px; color:#1B2A4A;">
            <b>Recovery message</b><br>{row['recovery_message']}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)