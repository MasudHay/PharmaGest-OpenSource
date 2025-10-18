# 💊 PharmaGest - Open Source Pharmacy Management System

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) 
[![Made with](https://img.shields.io/badge/Made%20with-Gemini%20AI%20%26%20Python-orange)](https://github.com/google/gemini-api)

Welcome to the **PharmaGest** repository, a stock management and Point of Sale (POS) project designed specifically for pharmacies and drugstores, particularly within the African context, starting with **Cameroon**.

---

## 🌟 Our Mission

As a young pharmacist in Cameroon, I found that most existing management software is expensive and often conflicts with the true spirit of **Open Source**. This project aims to provide a **free, robust, and scalable** solution to help small and medium-sized pharmacies manage inventory, batches (FIFO/LIFO), sales, and insurance without licensing costs.

This code was initially generated and structured with the help of **Gemini AI**, but it now needs the power of the open source community to evolve into a comprehensive professional tool.

## ✨ Current Features

PharmaGest is functional and currently includes:

* **Stock Management:** Tracking of drug batches (number, expiry date), alert thresholds, intake, and adjustments.
* **Point of Sale (POS):** Simple cashier interface for processing sales with batch decrement (FIFO logic).
* **Multi-User System:** User roles and permissions (Admin, Cashier, Salesperson).
* **Local Currency:** Use of **XAF** (CFA Franc).
* **Local Database:** Uses **SQLite** for straightforward single-machine deployment.
* **Graphical Interface (GUI):** Built using **Tkinter** (Python's native library).

---

## 🌍 Language and Localization

The **source code (variables, comments, functions)** and the **Graphical User Interface (GUI)** are currently written entirely in **French**.

As the initial developer is based in a bilingual country (Cameroon) but attended Francophone school, French was the starting language. We are actively seeking contributions to implement a robust **localization framework** to allow users to switch the GUI language easily. The immediate goal is to offer full support for **English** and **French**.

---

## 🚀 How to Contribute?

All help is welcome, regardless of your experience level!

### 1. Installation

To run the project locally, you must have **Python 3.8+** and Git installed.

```bash
# Clone the repository
git clone [https://github.com/MasudHay/PharmaGest-OpenSource.git](https://github.com/MasudHay/PharmaGest-OpenSource.git)
cd PharmaGest-OpenSource

# Create and activate the virtual environment (HIGHLY RECOMMENDED)
python3 -m venv venv
source venv/bin/activate  # On Windows (CMD): venv\Scripts\activate.bat

# Install dependencies 
# NOTE: Ensure you run 'pip freeze > requirements.txt' locally first
pip install -r requirements.txt 

# Run the application
python3 pharmagest_app.py
