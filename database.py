import sqlite3
from datetime import datetime

DB_NAME = "tekstil_erp.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    color TEXT NOT NULL,
                    size TEXT NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    cost_price REAL DEFAULT 0.0,
                    UNIQUE(product_name, color, size)
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    color TEXT NOT NULL,
                    size TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    sale_price REAL NOT NULL,
                    cost_price REAL NOT NULL,
                    channel TEXT NOT NULL,
                    commission_fee REAL DEFAULT 0.0,
                    shipping_cost REAL DEFAULT 0.0,
                    net_profit REAL NOT NULL,
                    sale_date TEXT NOT NULL
                )''')
    conn.commit()
    conn.close()

def get_all_stock():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM inventory ORDER BY product_name, color, size")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_or_update_variant(prod, color, size, qty, cost):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT quantity, cost_price FROM inventory WHERE product_name=? AND color=? AND size=?", 
              (prod.strip().lower(), color.strip().lower(), str(size).strip().upper()))
    row = c.fetchone()
    if row:
        new_qty = int(row[0]) + int(qty)
        c.execute("UPDATE inventory SET quantity=?, cost_price=? WHERE product_name=? AND color=? AND size=?",
                  (new_qty, float(cost), prod.strip().lower(), color.strip().lower(), str(size).strip().upper()))
    else:
        c.execute("INSERT INTO inventory (product_name, color, size, quantity, cost_price) VALUES (?, ?, ?, ?, ?)",
                  (prod.strip().lower(), color.strip().lower(), str(size).strip().upper(), int(qty), float(cost)))
    conn.commit()
    conn.close()

def record_sale(prod, color, size, qty, sale_price, channel="Mağaza", shipping_cost=0.0):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT quantity, cost_price FROM inventory WHERE product_name=? AND color=? AND size=?",
              (prod.strip().lower(), color.strip().lower(), str(size).strip().upper()))
    row = c.fetchone()
    if not row or row[0] < int(qty):
        conn.close()
        return False, "الكمية المطلوبة غير متوفرة في المستودع!"
    
    current_qty, cost_price = row[0], float(row[1])
    qty = int(qty)
    sale_price = float(sale_price)
    shipping_cost = float(shipping_cost)

    comm = (sale_price * 0.167 * qty) if channel.lower() == "trendyol" else 0.0
    ship = (shipping_cost * qty) if channel.lower() == "trendyol" else 0.0
    total_rev = sale_price * qty
    total_cost = cost_price * qty
    net_profit = total_rev - total_cost - comm - ship

    c.execute("UPDATE inventory SET quantity=? WHERE product_name=? AND color=? AND size=?",
              (current_qty - qty, prod.strip().lower(), color.strip().lower(), str(size).strip().upper()))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO sales (product_name, color, size, quantity, sale_price, cost_price, channel, commission_fee, shipping_cost, net_profit, sale_date)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (prod.strip().lower(), color.strip().lower(), str(size).strip().upper(), qty, sale_price, cost_price, channel, comm, ship, net_profit, now_str))
    
    conn.commit()
    conn.close()
    return True, {"net_profit": net_profit, "total_revenue": total_rev}

def get_financial_summary(days=1):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""SELECT 
                    COALESCE(SUM(quantity), 0),
                    COALESCE(SUM(sale_price * quantity), 0.0),
                    COALESCE(SUM(net_profit), 0.0)
                 FROM sales 
                 WHERE date(sale_date) >= date('now', '-' || cast(? as integer) || ' days')""", (int(days),))
    row = c.fetchone()
    conn.close()
    return {
        "total_sold": int(row[0]) if row and row[0] is not None else 0,
        "total_revenue": float(row[1]) if row and row[1] is not None else 0.0,
        "net_profit": float(row[2]) if row and row[2] is not None else 0.0
    }
