"""
Expense Tracker
A clean, minimal group expense sharing and smart settlement application.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

from engine import (
    calculate_net_balances,
    optimize_settlements,
    ExpenseIntelligence,
    parse_receipt_text,
    query_ai_financial_assistant
)

# Page configuration
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Clean, Professional Minimal CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #111827;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .app-title {
        text-align: center;
        font-size: 2rem;
        font-weight: 700;
        margin-top: 0.5rem;
        margin-bottom: 0.2rem;
        color: #111827;
    }
    
    .app-tagline {
        text-align: center;
        font-size: 0.95rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    
    .total-card {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    
    .total-label {
        font-size: 0.85rem;
        color: #6B7280;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
        margin-bottom: 0.2rem;
    }
    
    .total-amount {
        font-size: 2.5rem;
        font-weight: 700;
        color: #111827;
    }
    
    .item-row {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .badge-positive {
        background: #ECFDF5;
        color: #059669;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 8px;
        font-size: 0.85rem;
    }
    
    .badge-negative {
        background: #FEF2F2;
        color: #DC2626;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 8px;
        font-size: 0.85rem;
    }
    
    .badge-settled {
        background: #F3F4F6;
        color: #6B7280;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 8px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper for category icon
def get_cat_icon(cat):
    icons = {
        "Food & Dining": "🍔",
        "Transportation": "🚕",
        "Accommodation & Rent": "🏡",
        "Groceries": "🥑",
        "Entertainment": "🎳",
        "Health & Misc": "💊",
        "General / Misc": "🧾"
    }
    return icons.get(cat, "🧾")

# Initialize Session State
if "intelligence_engine" not in st.session_state:
    st.session_state.intelligence_engine = ExpenseIntelligence()

if "members" not in st.session_state:
    st.session_state.members = ["Vidhi", "Aarav", "Priya", "Rohan"]

if "constraints" not in st.session_state:
    st.session_state.constraints = []

if "expenses" not in st.session_state:
    st.session_state.expenses = [
        {
            "id": 1,
            "description": "Weekend Villa Stay",
            "payer": "Vidhi",
            "amount": 12000.0,
            "category": "Accommodation & Rent",
            "date": "Oct 10",
            "splits": {"Vidhi": 3000.0, "Aarav": 3000.0, "Priya": 3000.0, "Rohan": 3000.0}
        },
        {
            "id": 2,
            "description": "Royal Biryani Dinner",
            "payer": "Aarav",
            "amount": 2400.0,
            "category": "Food & Dining",
            "date": "Oct 11",
            "splits": {"Vidhi": 600.0, "Aarav": 600.0, "Priya": 600.0, "Rohan": 600.0}
        },
        {
            "id": 3,
            "description": "Airport Outstation Cab",
            "payer": "Priya",
            "amount": 1800.0,
            "category": "Transportation",
            "date": "Oct 11",
            "splits": {"Vidhi": 450.0, "Aarav": 450.0, "Priya": 450.0, "Rohan": 450.0}
        },
        {
            "id": 4,
            "description": "Party Snacks & Drinks",
            "payer": "Rohan",
            "amount": 1600.0,
            "category": "Groceries",
            "date": "Oct 12",
            "splits": {"Vidhi": 400.0, "Aarav": 400.0, "Priya": 400.0, "Rohan": 400.0}
        }
    ]

# Header
st.markdown('<div class="app-title">Expense Tracker</div>', unsafe_allow_html=True)
st.markdown('<div class="app-tagline">Manage group expenses, balances, and settlements</div>', unsafe_allow_html=True)

df_exp = pd.DataFrame(st.session_state.expenses)
balances = calculate_net_balances(st.session_state.members, st.session_state.expenses)
settlements = optimize_settlements(balances, st.session_state.constraints)
total_spend = df_exp["amount"].sum() if not df_exp.empty else 0.0

# Total Spend Overview
st.markdown(f"""
<div class="total-card">
    <div class="total-label">Total Group Expenses</div>
    <div class="total-amount">₹{total_spend:,.2f}</div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab_settle, tab_add, tab_scan, tab_ai = st.tabs(["Settlement", "Add Expense", "Scan Receipt", "Assistant"])

# ==========================================
# 1. SETTLEMENT
# ==========================================
with tab_settle:
    st.write("")
    st.subheader("Balances")
    
    col_l, col_r = st.columns(2)
    member_list = list(balances.items())
    half = (len(member_list) + 1) // 2

    for idx, (m, bal) in enumerate(member_list):
        target_col = col_l if idx < half else col_r
        with target_col:
            badge = f'<span class="badge-positive">Gets back ₹{bal:,.2f}</span>' if bal > 0 else (
                f'<span class="badge-negative">Owes ₹{abs(bal):,.2f}</span>' if bal < 0 else
                '<span class="badge-settled">Settled</span>'
            )
            st.markdown(f"""
            <div class="item-row">
                <span style="font-weight:600;">{m}</span>
                {badge}
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    st.subheader("Settlement Plan")
    if not settlements:
        st.success("All balances are settled.")
    else:
        for s in settlements:
            st.markdown(f"""
            <div class="item-row" style="background:#F9FAFB;">
                <div>
                    <b>{s['from']}</b> pays <b>{s['to']}</b>
                </div>
                <div style="font-weight:700; color:#059669; font-size:1.05rem;">₹{s['amount']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    st.subheader("Expense History")
    for exp in reversed(st.session_state.expenses):
        icon = get_cat_icon(exp["category"])
        st.markdown(f"""
        <div class="item-row">
            <div style="display:flex; align-items:center;">
                <span style="font-size:1.2rem; margin-right:0.75rem;">{icon}</span>
                <div>
                    <div style="font-weight:600;">{exp['description']}</div>
                    <div style="color:#6B7280; font-size:0.8rem;">{exp['date']} · Paid by {exp['payer']} · {exp['category']}</div>
                </div>
            </div>
            <div style="font-weight:700;">₹{exp['amount']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# 2. ADD EXPENSE
# ==========================================
with tab_add:
    st.write("")
    st.subheader("New Expense")
    
    with st.form("add_expense_form"):
        desc = st.text_input("Description", placeholder="e.g. Dinner, Taxi, Groceries")
        amt = st.number_input("Amount (₹)", min_value=1.0, value=500.0, step=50.0)
        payer = st.selectbox("Paid by", options=st.session_state.members)
        
        suggested = st.session_state.intelligence_engine.predict_category(desc)
        cat_choices = ["Food & Dining", "Transportation", "Accommodation & Rent", "Groceries", "Entertainment", "Health & Misc", "General / Misc"]
        default_i = cat_choices.index(suggested) if suggested in cat_choices else len(cat_choices) - 1
        category = st.selectbox("Category", cat_choices, index=default_i)
        
        split_type = st.radio("Split type", ["Equally", "Custom amounts"], horizontal=True)
        
        custom_splits = {}
        if split_type == "Custom amounts":
            st.write("Member shares:")
            c_cols = st.columns(len(st.session_state.members))
            for i, m in enumerate(st.session_state.members):
                with c_cols[i]:
                    custom_splits[m] = st.number_input(f"{m}", min_value=0.0, value=round(amt/len(st.session_state.members), 2), key=f"c_{m}")
        else:
            eq = round(amt / len(st.session_state.members), 2)
            custom_splits = {m: eq for m in st.session_state.members}
            
        submitted = st.form_submit_button("Save Expense")
        if submitted:
            new_id = len(st.session_state.expenses) + 1
            st.session_state.expenses.append({
                "id": new_id,
                "description": desc or "Shared Expense",
                "payer": payer,
                "amount": float(amt),
                "category": category,
                "date": datetime.now().strftime("%b %d"),
                "splits": custom_splits
            })
            st.success("Expense saved successfully.")
            st.rerun()


# ==========================================
# 3. SCAN RECEIPT
# ==========================================
with tab_scan:
    st.write("")
    st.subheader("Scan Receipt")
    
    demo_invoice = st.selectbox("Sample Receipt:", [
        "Restaurant Bill (₹1,837.00)",
        "Grocery Store (₹2,450.00)",
        "Fuel Station (₹3,200.00)"
    ])
    
    if "Restaurant" in demo_invoice:
        ocr_text = "THE URBAN BISTRO\n1x Gourmet Pizza 650.00\n2x Chocolate Shake 480.00\n1x Truffle Fries 320.00\n1x Coffee 220.00\nTOTAL 1837.00"
    elif "Grocery" in demo_invoice:
        ocr_text = "NATURES BASKET\nAlmond Milk 350.00\nFruits & Kiwi 600.00\nOlive Oil 950.00\nSourdough 250.00\nTOTAL 2450.00"
    else:
        ocr_text = "HP FUEL STATION\nPremium Petrol 3200.00\nTOTAL 3200.00"

    parsed = parse_receipt_text(ocr_text)
    
    st.markdown(f"""
    <div style="background:#F9FAFB; border:1px solid #E5E7EB; border-radius:12px; padding:1.2rem; margin:0.8rem 0;">
        <div style="font-size:0.85rem; color:#6B7280;">Merchant</div>
        <div style="font-size:1.2rem; font-weight:700; margin-bottom:0.3rem;">{parsed['merchant']}</div>
        <div style="font-size:1.8rem; font-weight:700;">₹{parsed['total']:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    scan_payer = st.selectbox("Paid by", options=st.session_state.members, key="scan_payer")
    if st.button("Add to Expenses"):
        eq = round(parsed["total"] / len(st.session_state.members), 2)
        st.session_state.expenses.append({
            "id": len(st.session_state.expenses) + 1,
            "description": f"{parsed['merchant']} (Receipt)",
            "payer": scan_payer,
            "amount": parsed["total"],
            "category": "Food & Dining" if "Bistro" in parsed["merchant"] else "Groceries",
            "date": datetime.now().strftime("%b %d"),
            "splits": {m: eq for m in st.session_state.members}
        })
        st.success("Receipt added to expenses.")
        st.rerun()


# ==========================================
# 4. ASSISTANT
# ==========================================
with tab_ai:
    st.write("")
    st.subheader("Financial Assistant")
    st.caption("Ask questions about group balances and spending.")
    
    c1, c2, c3 = st.columns(3)
    q1 = c1.button("Who owes the most?")
    q2 = c2.button("Why did trip cost so much?")
    q3 = c3.button("Who paid the highest total?")
    
    prompt = ""
    if q1:
        prompt = "Who owes the most?"
    elif q2:
        prompt = "Why did our trip cost more than expected?"
    elif q3:
        prompt = "Who has paid the most amount?"
        
    user_q = st.text_input("Question:", value=prompt, placeholder="Type your question here...")
    
    if user_q:
        ans = query_ai_financial_assistant(user_q, df_exp, balances, settlements)
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E5E7EB; border-left:4px solid #111827; border-radius:12px; padding:1.2rem; margin-top:1rem; font-size:0.92rem; line-height:1.6;">
            {ans}
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("<br><div style='text-align:center; color:#9CA3AF; font-size:0.8rem;'>Expense Tracker</div>", unsafe_allow_html=True)
