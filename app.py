
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
DB = BASE / "site_management.db"

app = Flask(__name__)
app.secret_key = "civil-site-demo-secret"
app.config["TODAY"] = datetime.now().strftime("%Y-%m-%d")


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        trade TEXT NOT NULL,
        contact TEXT,
        phone TEXT,
        tax_id TEXT,
        rating INTEGER DEFAULT 5,
        note TEXT
    );

    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        unit TEXT NOT NULL,
        min_stock REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS material_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER NOT NULL,
        vendor_id INTEGER,
        log_type TEXT NOT NULL CHECK(log_type IN ('進貨','領料')),
        quantity REAL NOT NULL,
        unit_price REAL DEFAULT 0,
        invoice_no TEXT,
        reconciled INTEGER DEFAULT 0,
        log_date TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE CASCADE,
        FOREIGN KEY(vendor_id) REFERENCES vendors(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        payee TEXT,
        expense_date TEXT NOT NULL,
        reimbursed INTEGER DEFAULT 0,
        note TEXT
    );

    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        borrower TEXT NOT NULL,
        checkout_date TEXT NOT NULL,
        return_date TEXT,
        status TEXT NOT NULL DEFAULT '借出',
        note TEXT
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT '行政',
        task_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT '待處理',
        note TEXT
    );
    """)

    conn.commit()
    conn.close()


def seed():
    conn = get_db()

