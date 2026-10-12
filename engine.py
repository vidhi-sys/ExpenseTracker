"""
SpendSense AI - Core Engine Modules:
1. Smart Settlement Optimizer 2.0 (Greedy min-cash-flow with UPI/payment constraints & unequal splits)
2. ML Expense Intelligence (TF-IDF Category Classifier & Isolation Forest Anomaly Detector)
3. Receipt Scanner (OCR + Heuristic parser)
4. AI Financial Assistant Grounding Engine
"""

import re
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest
import heapq

# -------------------------------------------------------------
# 1. SMART SETTLEMENT OPTIMIZER 2.0
# -------------------------------------------------------------
def calculate_net_balances(members, expenses):
    """
    Computes net balance for each member.
    expenses = [
      {
         "payer": "Alice",
         "amount": 1200.0,
         "split_type": "EQUAL" / "EXACT" / "PERCENT",
         "splits": {"Alice": 400.0, "Bob": 400.0, "Charlie": 400.0} # or shares
      }
    ]
    """
    balances = {m: 0.0 for m in members}
    for exp in expenses:
        payer = exp["payer"]
        amount = float(exp["amount"])
        balances[payer] = balances.get(payer, 0.0) + amount

        splits = exp["splits"]
        for debtor, share in splits.items():
            balances[debtor] = balances.get(debtor, 0.0) - float(share)
            
    # Round to 2 decimals to prevent floating point noise
    return {k: round(v, 2) for k, v in balances.items()}


def optimize_settlements(balances, constraints=None):
    """
    Minimizes transfer transactions using greedy two-pointer/heap matching.
    Supports constraints: e.g. prohibited routes or preferred direct channels.
    balances: dict(member: net_balance)
    constraints: list of dicts or tuples e.g. [("Alice", "Bob", "BLOCKED")]
    Returns: list of {from, to, amount, channel}
    """
    if constraints is None:
        constraints = []
        
    blocked_edges = set()
    for c in constraints:
        if c.get("type") == "BLOCKED":
            blocked_edges.add((c["from"], c["to"]))

    # Separate creditors (+) and debtors (-)
    creditors = []
    debtors = []

    for person, bal in balances.items():
        if bal > 0.01:
            creditors.append([person, bal])
        elif bal < -0.01:
            debtors.append([person, -bal])

    # Sort descending by balance magnitude
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    settlements = []
    
    i = 0  # debtors pointer
    j = 0  # creditors pointer

    while i < len(debtors) and j < len(creditors):
        debtor, d_amt = debtors[i]
        creditor, c_amt = creditors[j]

        if d_amt <= 0.01:
            i += 1
            continue
        if c_amt <= 0.01:
            j += 1
            continue

        # Check if route is blocked
        if (debtor, creditor) in blocked_edges:
            # Try next creditor if available
            if j + 1 < len(creditors):
                creditor, c_amt = creditors[j + 1]
                settle_amt = min(d_amt, c_amt)
                settlements.append({
                    "from": debtor,
                    "to": creditor,
                    "amount": round(settle_amt, 2),
                    "mode": "Alternative UPI / Bank Transfer (Constraint Applied)"
                })
                debtors[i][1] -= settle_amt
                creditors[j + 1][1] -= settle_amt
                continue

        settle_amt = min(d_amt, c_amt)
        settlements.append({
            "from": debtor,
            "to": creditor,
            "amount": round(settle_amt, 2),
            "mode": "Instant UPI / QR"
        })

        debtors[i][1] -= settle_amt
        creditors[j][1] -= settle_amt

        if debtors[i][1] <= 0.01:
            i += 1
        if creditors[j][1] <= 0.01:
            j += 1

    return settlements


# -------------------------------------------------------------
# 2. ML EXPENSE INTELLIGENCE (Classification + Anomaly Detection)
# -------------------------------------------------------------
class ExpenseIntelligence:
    def __init__(self):
        # Seed training dataset
        sample_data = [
            ("Swiggy Biryani Dinner", "Food & Dining"),
            ("Zomato Pizza order", "Food & Dining"),
            ("Starbucks iced latte", "Food & Dining"),
            ("Uber cab to airport", "Transportation"),
            ("Ola city ride", "Transportation"),
            ("Metro recharge ticket", "Transportation"),
            ("Petrol gas refill", "Transportation"),
            ("Airbnb weekend villa stay", "Accommodation & Rent"),
            ("Monthly shared apartment rent", "Accommodation & Rent"),
            ("Hotel booking deposit", "Accommodation & Rent"),
            ("Groceries Blinkit quick delivery", "Groceries"),
            ("Zepto milk veggies fruits", "Groceries"),
            ("Nature Basket organic food", "Groceries"),
            ("Netflix monthly group plan", "Entertainment"),
            ("PVR Cinema movie tickets IMAX", "Entertainment"),
            ("Board games arcade bowling", "Entertainment"),
            ("Amazon pharmacy medicine", "Health & Misc"),
            ("First aid kit and medicines", "Health & Misc")
        ]
        X = [item[0] for item in sample_data]
        y = [item[1] for item in sample_data]

        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
        X_vec = self.vectorizer.fit_transform(X)
        self.clf = LogisticRegression(max_iter=200)
        self.clf.fit(X_vec, y)

        # Baseline anomaly detector
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        baseline_amounts = np.array([[80], [150], [300], [450], [600], [1200], [1500], [2200], [2500], [3000]])
        self.anomaly_detector.fit(baseline_amounts)

    def predict_category(self, description):
        if not description or not description.strip():
            return "General / Misc"
        vec = self.vectorizer.transform([description])
        probs = self.clf.predict_proba(vec)[0]
        max_idx = np.argmax(probs)
        conf = probs[max_idx]
        if conf < 0.25:
            return "General / Misc"
        return self.clf.classes_[max_idx]

    def detect_anomalies(self, df_expenses):
        """
        Detects unusually high or irregular spending in group history.
        """
        if len(df_expenses) < 4:
            # Simple threshold check if few samples
            mean_amt = df_expenses["amount"].mean() if len(df_expenses) > 0 else 0
            std_amt = df_expenses["amount"].std() if len(df_expenses) > 1 else 0
            is_anomaly = df_expenses["amount"] > (mean_amt + 2 * (std_amt or mean_amt or 1))
            return is_anomaly

        amounts = df_expenses[["amount"]].values
        # Isolation Forest fit on current group expenditure
        iso = IsolationForest(contamination=0.12, random_state=42)
        preds = iso.fit_predict(amounts)
        return preds == -1


# -------------------------------------------------------------
# 3. RECEIPT OCR & PARSING ENGINE
# -------------------------------------------------------------
def parse_receipt_text(ocr_text):
    """
    Extracts Merchant name, Date, Total amount, and Line items using regex heuristics.
    """
    lines = [line.strip() for line in ocr_text.split("\n") if line.strip()]
    merchant = "Unknown Merchant"
    total = 0.0
    date = "2026-10-12"
    items = []

    # First non-empty line often merchant
    for line in lines[:3]:
        clean = re.sub(r'[^a-zA-Z\s&]', '', line).strip()
        if len(clean) >= 3:
            merchant = clean
            break

    # Look for date pattern YYYY-MM-DD or DD/MM/YYYY or DD-MM-YYYY
    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', ocr_text)
    if date_match:
        date = date_match.group(1)

    # Line item regex: Name followed by price
    # e.g. "Chicken Burger  250.00"
    for line in lines:
        price_match = re.search(r'(?:total|subtotal|balance|due)?.*?(\d+[\.,]\d{2}|\d{3,6})', line, re.IGNORECASE)
        is_total = re.search(r'\b(total|grand total|amount due|net)\b', line, re.IGNORECASE)
        
        amounts = re.findall(r'(\d+(?:\.\d{1,2})?)', line)
        if amounts:
            try:
                amt = float(amounts[-1])
                if is_total and amt > total:
                    total = amt
                elif not is_total and len(line) > 3 and amt > 0:
                    item_name = re.sub(r'[\d\.,\$:₹]', '', line).strip()
                    if len(item_name) >= 2:
                        items.append({"item": item_name, "cost": amt})
            except Exception:
                pass

    if total == 0.0 and items:
        total = sum(i["cost"] for i in items)

    return {
        "merchant": merchant,
        "date": date,
        "total": round(total, 2),
        "items": items
    }


# -------------------------------------------------------------
# 4. GROUNDED AI ASSISTANT QUERY ENGINE
# -------------------------------------------------------------
def query_ai_financial_assistant(prompt, df_expenses, balances, settlements):
    """
    Deterministic NLP & Grounded Query Engine for group questions.
    """
    p = prompt.lower()
    
    if "highest" in p or "owes the most" in p or "max debt" in p:
        debtors = {k: v for k, v in balances.items() if v < 0}
        if not debtors:
            return "🎉 Everyone is square! There are no outstanding negative balances."
        max_debtor = min(debtors, key=debtors.get)
        return (f"📊 **Highest Unpaid Balance:** **{max_debtor}** owes the group **₹{abs(debtors[max_debtor]):.2f}**.\n\n"
                f"Breakdown of all debtors:\n" +
                "\n".join([f"- **{k}**: owes ₹{abs(v):.2f}" for k, v in debtors.items()]))

    if "paid the most" in p or "who paid" in p or "top payer" in p:
        payers = df_expenses.groupby("payer")["amount"].sum().to_dict()
        if not payers:
            return "No expenses recorded yet."
        top_payer = max(payers, key=payers.get)
        return (f"💳 **Top Spender:** **{top_payer}** has fronted the highest total: **₹{payers[top_payer]:.2f}** "
                f"({(payers[top_payer]/df_expenses['amount'].sum())*100:.1f}% of all group expenses).")

    if "why did" in p and ("cost" in p or "trip" in p or "high" in p or "more" in p):
        cat_sums = df_expenses.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_cat = cat_sums.index[0]
        top_cat_amt = cat_sums.iloc[0]
        top_single = df_expenses.sort_values(by="amount", ascending=False).iloc[0]
        
        return (f"🔍 **Expense Driver Analysis:**\n\n"
                f"1. **Dominant Category:** `{top_cat}` accounted for **₹{top_cat_amt:.2f}** "
                f"({(top_cat_amt/df_expenses['amount'].sum())*100:.1f}% of total).\n"
                f"2. **Single Biggest Item:** '{top_single['description']}' paid by {top_single['payer']} costing **₹{top_single['amount']:.2f}**.\n"
                f"3. **Spending distribution:** {len(df_expenses)} total transactions logged.")

    if "settle" in p or "how to pay" in p or "transfers" in p:
        if not settlements:
            return "✅ All accounts are balanced! No transfers needed."
        res = "📋 **Recommended Minimum Transfer Plan:**\n\n"
        for idx, s in enumerate(settlements, 1):
            res += f"{idx}. **{s['from']}** ➔ pays **{s['to']}**: **₹{s['amount']:.2f}** via *{s['mode']}*\n"
        return res

    if "category" in p or "breakdown" in p:
        cat_sums = df_expenses.groupby("category")["amount"].sum().to_dict()
        res = "🏷️ **Category Spending Breakdown:**\n\n"
        for c, val in cat_sums.items():
            res += f"- **{c}**: ₹{val:.2f}\n"
        return res

    # General fallback summary
    total_spend = df_expenses["amount"].sum() if not df_expenses.empty else 0
    return (f"💡 **Group Financial Summary:**\n"
            f"- Total Group Expenditure: **₹{total_spend:.2f}**\n"
            f"- Total Transactions: **{len(df_expenses)}**\n"
            f"- Active Settling Members: **{len(balances)}**\n"
            f"You can ask me specific questions like: *'Who owes the most?'*, *'Why did the trip cost so much?'*, or *'How should we settle up?'*.")
