import sqlite3
import io
import os
import pandas as pd
from datetime import datetime as dt, timedelta

DB_FILE = "inventory.db"
TRENDYOL_COMMISSION_RATE = 0.167
LOW_STOCK_THRESHOLD = 3

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            color TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            cost_price REAL NOT NULL,
            image_path TEXT DEFAULT NULL,
            UNIQUE(product_name, color, size)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            color TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            cost_price REAL NOT NULL,
            sale_price REAL NOT NULL,
            channel TEXT NOT NULL,
            deductions REAL DEFAULT 0.0,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_or_update_variant(prod, color, size, qty, cost, image_path=None):
    conn = get_db()
    cursor = conn.cursor()
    prod = prod.strip().lower()
    color = color.strip().lower()
    size = str(size).strip().upper()
    
    cursor.execute("""
        INSERT INTO variants (product_name, color, size, quantity, cost_price, image_path)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(product_name, color, size) DO UPDATE SET
        quantity = quantity + excluded.quantity,
        cost_price = excluded.cost_price,
        image_path = COALESCE(excluded.image_path, variants.image_path)
    """, (prod, color, size, qty, cost, image_path))
    conn.commit()
    conn.close()

def get_all_stock():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_name, color, size, quantity, cost_price, image_path
        FROM variants
        ORDER BY product_name ASC, color ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def record_sale(prod, color, size, qty, sale_price, channel="Mağaza", shipping_cost=0.0):
    conn = get_db()
    cursor = conn.cursor()
    prod = prod.strip().lower()
    color = color.strip().lower()
    size = str(size).strip().upper()

    cursor.execute("SELECT id, quantity, cost_price FROM variants WHERE product_name = ? AND color = ? AND size = ?", (prod, color, size))
    row = cursor.fetchone()
    if not row or row["quantity"] < qty:
        conn.close()
        return False, "المخزون غير كافٍ أو المنتج غير مسجل!"

    v_id = row["id"]
    curr_qty = row["quantity"]
    cost = row["cost_price"]

    gross_revenue = sale_price * qty
    deductions = (gross_revenue * TRENDYOL_COMMISSION_RATE + shipping_cost) if channel == "Trendyol" else 0.0
    net_profit = gross_revenue - deductions - (cost * qty)

    cursor.execute("UPDATE variants SET quantity = ? WHERE id = ?", (curr_qty - qty, v_id))
    cursor.execute("""
        INSERT INTO sales (product_name, color, size, quantity, cost_price, sale_price, channel, deductions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (prod, color, size, qty, cost, sale_price, channel, deductions))
    conn.commit()
    conn.close()
    return True, {
        "product": prod, "color": color, "size": size,
        "quantity": qty, "net_profit": net_profit, "remaining": curr_qty - qty
    }

def get_financial_summary(days=1):
    start_date = dt.now().strftime("%Y-%m-%d 00:00:00") if days == 1 else (dt.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COALESCE(SUM(quantity), 0) as total_qty,
            COALESCE(SUM(cost_price * quantity), 0) as total_cost,
            COALESCE(SUM(sale_price * quantity), 0) as total_revenue,
            COALESCE(SUM(deductions), 0) as total_deductions
        FROM sales
        WHERE sale_date >= ?
    """, (start_date,))
    row = cursor.fetchone()
    conn.close()

    total_qty = row["total_qty"]
    total_cost = row["total_cost"]
    total_rev = row["total_revenue"]
    total_ded = row["total_deductions"]
    net_profit = total_rev - total_ded - total_cost

    return {
        "total_sold": total_qty,
        "total_revenue": total_rev,
        "total_cost": total_cost,
        "total_deductions": total_ded,
        "net_profit": net_profit
    }

def export_excel_bytes():
    conn = get_db()
    df_stock = pd.read_sql_query("SELECT product_name AS [المنتج], color AS [اللون], size AS [المقاس], quantity AS [المخزون], cost_price AS [التكلفة] FROM variants", conn)
    df_sales = pd.read_sql_query("SELECT sale_date AS [التاريخ], channel AS [القناة], product_name AS [المنتج], color AS [اللون], size AS [المقاس], quantity AS [العدد], sale_price AS [سعر البيع], deductions AS [الخصم] FROM sales ORDER BY id DESC", conn)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_stock.to_excel(writer, sheet_name='المخزون', index=False)
        df_sales.to_excel(writer, sheet_name='المبيعات', index=False)
    output.seek(0)
    return output.getvalue()
