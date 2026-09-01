import sqlite3
import datetime
import re
import flet as ft

# --- تهيئة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            color TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            cost_price REAL NOT NULL,
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

def main(page: ft.Page):
    init_db()
    page.title = "M&E Tekstil ERP"
    page.padding = 12
    page.scroll = ft.ScrollMode.AUTO
    page.bgcolor = "#F8FAFC"

    stat_total_stock = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color="#1E3A8A")
    stat_today_sales = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color="#312E81")
    stat_today_profit = ft.Text("0.00 TL", size=18, weight=ft.FontWeight.BOLD, color="#14532D")

    stock_list_view = ft.Column(spacing=8)
    all_stock_data = []

    search_input = ft.TextField(
        hint_text="ابحث عن موديل، لون، مقاس...",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=12,
        bgcolor="#FFFFFF",
        dense=True,
        on_change=lambda e: filter_stock(e.control.value)
    )

    def update_metrics():
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(quantity) FROM variants")
        tot_stock = cursor.fetchone()[0] or 0
        stat_total_stock.value = f"{tot_stock} قطعة"

        today_str = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
        cursor.execute("""
            SELECT SUM(quantity), SUM((sale_price - cost_price) * quantity - deductions)
            FROM sales WHERE sale_date >= ?
        """, (today_str,))
        s_row = cursor.fetchone()
        t_qty = s_row[0] or 0
        t_profit = s_row[1] or 0.0
        stat_today_sales.value = f"{t_qty} قطعة"
        stat_today_profit.value = f"+{t_profit:.2f} TL"
        conn.close()

    def load_stock():
        nonlocal all_stock_data
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_name, color, size, quantity, cost_price FROM variants ORDER BY product_name ASC, color ASC")
        all_stock_data = cursor.fetchall()
        conn.close()
        update_metrics()
        render_stock(all_stock_data)

    def render_stock(items):
        stock_list_view.controls.clear()
        if not items:
            stock_list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=48, color="#94A3B8"),
                            ft.Text("لا توجد منتجات مسجلة في المخزن", color="#64748B", size=15)
                        ]
                    ),
                    alignment=ft.Alignment(0, 0),
                    padding=30
                )
            )
        else:
            for item in items:
                v_id, name, color, size, qty, cost = item
                status_color = "#16A34A" if qty > 3 else ("#EA580C" if qty > 0 else "#DC2626")
                status_text = "متوفر" if qty > 3 else ("قليل" if qty > 0 else "نفد")

                card = ft.Container(
                    padding=14,
                    border_radius=14,
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, "#E2E8F0"),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Text(f"{name.title()} ({color.title()})", size=16, weight=ft.FontWeight.BOLD, color="#0F172A"),
                                            ft.Container(
                                                content=ft.Text(size, size=12, weight=ft.FontWeight.BOLD, color="#1D4ED8"),
                                                bgcolor="#EFF6FF",
                                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                                border_radius=6
                                            )
                                        ]
                                    ),
                                    ft.Text(f"التكلفة: {cost:.2f} TL", size=13, color="#64748B"),
                                    ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.Icon(ft.Icons.CIRCLE, size=8, color=status_color),
                                            ft.Text(f"{qty} قطعة ({status_text})", size=13, weight=ft.FontWeight.W_500, color=status_color)
                                        ]
                                    )
                                ]
                            ),
                            ft.ElevatedButton(
                                "بيع",
                                icon=ft.Icons.SHOPPING_BAG_OUTLINED,
                                bgcolor="#16A34A",
                                color="#FFFFFF",
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                                on_click=lambda e, vid=v_id, n=name, c=color, s=size, q=qty, cp=cost: open_sale_dialog(vid, n, c, s, q, cp)
                            )
                        ]
                    )
                )
                stock_list_view.controls.append(card)
        page.update()

    def filter_stock(query):
        q = query.strip().lower()
        if not q:
            render_stock(all_stock_data)
        else:
            filtered = [
                it for it in all_stock_data
                if q in it[1].lower() or q in it[2].lower() or q in it[3].lower()
            ]
            render_stock(filtered)

    # --- نافذة اللصق الذكي (Smart Paste) ---
    def open_smart_paste_dialog(e):
        paste_input = ft.TextField(
            label="الصق النص أو الجدول هنا",
            multiline=True,
            min_lines=6,
            max_lines=10,
            hint_text="مثال:\nZara Krep Pantolon\nالتكلفة: 140\nالمقاسات: 34, 36, 38, 40, 42, 44\nsiyah: 7, 7, 14, 14, 7, 7\nlaci: 1, 1, 2, 2, 1, 1\nbordo: 5, 5, 10, 10, 5, 5",
            border_radius=8
        )

        def process_paste_text(ev):
            raw = paste_input.value.strip()
            if not raw:
                return

            lines = [l.strip() for l in raw.split("\n") if l.strip()]
            model_name = "zara krep pantolon"
            cost_price = 140.0
            sizes = ["34", "36", "38", "40", "42", "44"]
            parsed_items = []

            for line in lines:
                l_low = line.lower()
                if "تكلفة" in l_low or "maliyet" in l_low or "cost" in l_low or "fiyat" in l_low:
                    m = re.search(r'(\d+(?:[.,]\d+)?)', l_low)
                    if m:
                        cost_price = float(m.group(1).replace(",", "."))
                elif "مقاس" in l_low or "beden" in l_low or "size" in l_low:
                    parts = re.split(r'[:=]', line, 1)
                    if len(parts) > 1:
                        sizes = [s.strip().upper() for s in re.split(r'[, \t]+', parts[1]) if s.strip()]
                elif ":" in line:
                    c_name, q_str = line.split(":", 1)
                    c_name = c_name.strip().lower()
                    raw_nums = re.findall(r'\d+', q_str)
                    if raw_nums:
                        quantities = [int(n) for n in raw_nums]
                        for i, q in enumerate(quantities):
                            s = sizes[i] if i < len(sizes) else str(34 + (i * 2))
                            parsed_items.append((model_name, c_name, s, q, cost_price))
                elif len(line.split()) >= 2 and not any(k in l_low for k in ["stok", "adet", "tl", "toplam"]):
                    model_name = line.strip().lower()

            if not parsed_items:
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ تعذر استخراج البيانات، تأكد من التنسيق."), bgcolor="#DC2626")
                page.snack_bar.open = True
                page.update()
                return

            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            total_added = 0
            for item in parsed_items:
                total_added += item[3]
                cursor.execute("""
                    INSERT INTO variants (product_name, color, size, quantity, cost_price)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(product_name, color, size) DO UPDATE SET
                    quantity = quantity + excluded.quantity,
                    cost_price = excluded.cost_price
                """, item)
            conn.commit()
            conn.close()

            smart_dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ تم استيراد {total_added} قطعة وتوزيعها بنجاح!"), bgcolor="#16A34A")
            page.snack_bar.open = True
            load_stock()

        def close_dialog(ev):
            smart_dialog.open = False
            page.update()

        smart_dialog = ft.AlertDialog(
            title=ft.Text("📋 لصق نص ذكي واستيراد سريع"),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text("انسخ جدول الإكسل أو رسالة التوزيع والصقها هنا:", size=13, color="#64748B"),
                    paste_input
                ]
            ),
            actions=[
                ft.TextButton("إلغاء", on_click=close_dialog),
                ft.ElevatedButton("معالجة وحفظ في المخزن", on_click=process_paste_text, bgcolor="#4F46E5", color="#FFFFFF")
            ]
        )

        page.dialog = smart_dialog
        smart_dialog.open = True
        page.update()

    # --- نافذة تسجيل البيع ---
    def open_sale_dialog(variant_id, name, color, size, max_qty, cost_price):
        qty_input = ft.TextField(label="الكمية المباعة", value="1", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8)
        price_input = ft.TextField(label="سعر البيع للقطعة (TL)", value="250", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8)
        channel_dropdown = ft.Dropdown(
            label="منصة البيع",
            value="Mağaza",
            border_radius=8,
            options=[
                ft.dropdown.Option("Mağaza"),
                ft.dropdown.Option("Trendyol"),
                ft.dropdown.Option("Toptan")
            ]
        )

        def confirm_sale(e):
            try:
                sale_qty = int(qty_input.value)
                sale_price = float(price_input.value)
                channel = channel_dropdown.value
            except ValueError:
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ يرجى إدخال أرقام صحيحة!"), bgcolor="#DC2626")
                page.snack_bar.open = True
                page.update()
                return

            if sale_qty <= 0 or sale_qty > max_qty:
                page.snack_bar = ft.SnackBar(ft.Text(f"⚠️ الكمية غير صالحة! المتوفر: {max_qty}"), bgcolor="#DC2626")
                page.snack_bar.open = True
                page.update()
                return

            deductions = (sale_price * sale_qty * 0.167) if channel == "Trendyol" else 0.0

            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE variants SET quantity = quantity - ? WHERE id = ?", (sale_qty, variant_id))
            cursor.execute("""
                INSERT INTO sales (product_name, color, size, quantity, cost_price, sale_price, channel, deductions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, color, size, sale_qty, cost_price, sale_price, channel, deductions))
            conn.commit()
            conn.close()

            dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ تم تسجيل بيع {sale_qty} قطعة بنجاح!"), bgcolor="#16A34A")
            page.snack_bar.open = True
            load_stock()

        def close_dialog(e):
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(f"تسجيل بيع: {name.title()} ({color.title()})"),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    ft.Text(f"المقاس: {size} | المتوفر: {max_qty} قطعة", color="#475569", weight=ft.FontWeight.W_500),
                    qty_input,
                    price_input,
                    channel_dropdown
                ]
            ),
            actions=[
                ft.TextButton("إلغاء", on_click=close_dialog),
                ft.ElevatedButton("تأكيد وخصم", on_click=confirm_sale, bgcolor="#16A34A", color="#FFFFFF")
            ]
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    # --- شريط التطبيق العلوي ---
    page.appbar = ft.AppBar(
        title=ft.Text("M&E Tekstil ERP", weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        center_title=True,
        bgcolor="#0F172A",
        actions=[
            ft.IconButton(ft.Icons.REFRESH, tooltip="تحديث", icon_color="#FFFFFF", on_click=lambda e: load_stock())
        ]
    )

    def kpi_card(title, value_widget, icon, bg_color):
        return ft.Container(
            expand=True,
            padding=12,
            border_radius=12,
            bgcolor=bg_color,
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(title, size=11, color="#475569", weight=ft.FontWeight.W_500),
                            ft.Icon(icon, size=16, color="#475569")
                        ]
                    ),
                    value_widget
                ]
            )
        )

    dashboard_row = ft.Row(
        spacing=8,
        controls=[
            kpi_card("إجمالي المخزن", stat_total_stock, ft.Icons.INVENTORY_2, "#EFF6FF"),
            kpi_card("مبيعات اليوم", stat_today_sales, ft.Icons.SHOPPING_BAG, "#EEF2FF"),
            kpi_card("أرباح اليوم", stat_today_profit, ft.Icons.ATTACH_MONEY, "#F0FDF4"),
        ]
    )

    action_bar = ft.Row(
        spacing=8,
        controls=[
            ft.ElevatedButton(
                "📋 لصق نص ذكي",
                icon=ft.Icons.PASTE,
                bgcolor="#4F46E5",
                color="#FFFFFF",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                on_click=open_smart_paste_dialog
            ),
        ]
    )

    page.add(
        dashboard_row,
        ft.Container(height=4),
        action_bar,
        ft.Container(height=4),
        search_input,
        ft.Container(height=4),
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("📦 قائمة المخزون", size=16, weight=ft.FontWeight.BOLD, color="#0F172A"),
            ]
        ),
        stock_list_view
    )

    load_stock()

ft.app(target=main)
                    
