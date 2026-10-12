# Expense Tracker

A clean, minimalist group expense sharing and settlement application built with Python and Streamlit.

## Features

- **Balances & Settlement**: Calculates individual net balances and minimizes total transfer transactions using greedy debt simplification.
- **Add Expenses**: Split shared expenses equally or by custom amounts with automatic category detection.
- **Receipt Scanner**: Extracts merchant names and bill totals from receipts and adds them directly to the ledger.
- **Financial Assistant**: Answers natural language questions regarding balances, spending drivers, and settlements.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run app.py
```

3. Open your browser at `http://localhost:8501`.

## Project Structure

```text
├── app.py              # Main Streamlit web application
├── engine.py           # Settlement algorithms, ML categorization, and assistant engine
├── requirements.txt    # Project dependencies
└── README.md           # Documentation
```
