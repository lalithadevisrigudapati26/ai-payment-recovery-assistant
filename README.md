# 💳 AI Payment Recovery Assistant

**Turning failed payments into recovered revenue — intelligently, and at a cost that scales.**

Built for the Razorpay AI Builder Internship 2026 (AI Revenue Recovery track).

---

## The Problem

Every failed payment is a business decision hiding in plain sight. Some failures are just technical hiccups — a timeout, an expired session — where the customer still wants to pay. Others, like insufficient funds, need a different approach entirely. Most businesses treat every failure the same way: one generic retry message, sent to everyone, with no sense of priority or personalization.

At scale, that's a missed opportunity. This project explores a smarter way to think about it.

## What This Does

Upload a list of failed transactions. The system:

1. **Scores every transaction by recovery priority** — based on transaction value and how recoverable the failure type typically is
2. **Selectively applies AI** — only high-priority transactions get a full AI-personalized explanation and recovery message; lower-priority ones get a fast, free, rule-based template. This keeps cost proportional to value, instead of spending AI budget uniformly on every case
3. **Estimates recovery likelihood** per transaction, based on failure-type patterns
4. **Recommends a communication channel** (WhatsApp, Email, SMS) per transaction, based on urgency
5. **Calculates estimated ROI** — cost of AI usage vs. expected recovered revenue
6. **Presents everything in a live dashboard** — sortable, filterable, and exportable

## Why the Tiered AI Strategy Matters

A naive implementation calls an AI model for every single failed transaction. That doesn't scale — cost grows linearly with volume, even for low-value cases where a generic message works just as well.

This project instead asks: **where does personalization actually move the needle?** High-value, easily-recoverable transactions get full AI treatment. Everything else gets a solid, free template. This is a deliberate cost-vs-impact tradeoff, not a limitation — the kind of decision a production system would need to make.

## How This Fits Alongside Razorpay's Existing Tools

Razorpay already has strong infrastructure for automated retries and multichannel notifications for failed payments. This project isn't trying to replace that — it explores a complementary layer: **AI-driven personalization and prioritization**, deciding *which* customers deserve a uniquely-reasoned message versus a standard automated one. The priority scoring here could plug into an existing recovery pipeline as a decision layer, not a replacement for it.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend / Dashboard | Streamlit |
| AI Reasoning | Google Gemini API |
| Data Handling | Pandas |
| Language | Python |

## Architecture

```
Raw failed transactions (CSV)
        │
        ▼
 Priority Scoring Engine  ──►  High priority? 
        │                          │
        │                    Yes ──┴── No
        │                     │         │
        │                     ▼         ▼
        │              AI-Personalized  Rule-Based
        │              (Gemini API)     Template
        │                     │         │
        │                     └────┬────┘
        │                          ▼
        │                Recovery Likelihood +
        │                Recommended Channel
        │                          │
        ▼                          ▼
         Interactive Dashboard (Streamlit)
   Charts • ROI estimate • Filters • Export
```

## Running Locally

1. Clone this repo
   ```
   git clone https://github.com/lalithadevisrigudapati26/ai-payment-recovery-assistant.git
   cd ai-payment-recovery-assistant
   ```

2. Install dependencies
   ```
   pip install -r requirements.txt
   ```

3. Add your own Gemini API key
   Create a `.env` file in the project root:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   Get a free key at [aistudio.google.com](https://aistudio.google.com)

4. Run the dashboard
   ```
   streamlit run app.py
   ```

5. Try it: use the sample data instantly, or download the in-app template, fill in your own failed transactions, and upload it to see live AI analysis.

## What I'd Build Next

- Real send integration (WhatsApp Business API / email / SMS) instead of drafting messages only
- Replace illustrative recovery-likelihood and ROI figures with real historical conversion data
- A/B testing framework to measure AI-personalized vs. templated message performance in practice
- Support for larger datasets with batched/async AI calls and caching

## Honest Limitations

- Sample data is synthetic (15 transactions) — built to demonstrate the approach, not trained on real transaction volume
- Recovery likelihood percentages are rule-based estimates, not derived from historical outcome data
- No live message-sending capability yet — this is the decision layer, not the delivery layer

---

Built as part of the Razorpay AI Builder Internship 2026 buildathon.
