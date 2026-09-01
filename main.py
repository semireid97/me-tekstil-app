import sqlite3
import datetime
import re
import os
import csv
import flet as ft

def get_safe_db_path():
    try:
        data_dir = os.environ.get("FLET_APP_STORAGE_DATA")
        if data_dir and os.path.exists(data_dir):
            return os.path.join(data_dir, "app_inventory.db")
        home_dir = os.environ.get("HOME") or os.path.expanduser("~")
        if home_dir and os.path.exists(home_dir):
            return os.path.join(home_dir, "app_inventory.db")
    except Exception:
        pass
    return "app_inventory.db"

def init_db():
    db_path = get_safe_db_path()
    conn = sqlite3.connect(db_path)
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
    page.title = "M&E Tekstil ERP"
    page.padding = 10
    page.scroll = ft.ScrollMode.AUTO
    page.bgcolor = "#F8FAFC"

    try:
        init_db()
    except Exception as err:
        page.add(ft.Text(f"DB Error: {err}", color="red"))
        page.update()
        return

    stat_total_stock = ft.Text("0", size=15, weight=ft.FontWeight.BOLD, color="#1E3A8A")
    stat_today_sales = ft.Text("0", size=15, weight=ft.FontWeight.BOLD, color="#312E81")
    stat_today_profit = ft.Text("0.00 TL", size=15, weight=ft.FontWeight.BOLD, color="#14532D")

    stock_list_view = ft.Column(spacing=8)
    all_stock_data = []

    status_banner = ft.Container(visible=False, padding=10, border_radius=8)
    status_text = ft.Text("", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD)
    status_banner.content = status_text

    def show_in_page_alert(msg, is_error=False):
        status_banner.bgcolor = "#DC2626" if is_error else "#16A34A"
        status_text.value = msg
        status_banner.visible = True
        page.update()

    def update_metrics():
        try:
            conn = sqlite3.connect(get_safe_db_path())
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
        except Exception:
            pass

    def render_stock(items):
        stock_list_view.controls.clear()
        if not items:
            stock_list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.icons.INVENTORY_2_OUTLINED, size=40, color="#94A3B8"),
                            ft.Text("المخزن فارغ حالياً", color="#64748B", size=14)
                        ]
                    ),
                    padding=20
                )
            )
        else:
            for item in items:
                v_id, name, color, size, qty, cost = item
                status_color = "#16A34A" if qty > 3 else ("#EA580C" if qty > 0 else "#DC2626")
                status_text_val = "متوفر" if qty > 3 else ("قليل" if qty > 0 else "نفد")

                card = ft.Container(
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.colors.WHITE,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Text(f"{name.title()} ({color.title()})", size=14, weight=ft.FontWeight.BOLD, color="#0F172A"),
                                            ft.Container(
                                                content=ft.Text(size, size=11, weight=ft.FontWeight.BOLD, color="#1D4ED8"),
                                                bgcolor="#EFF6FF",
                                                padding=4,
                                                border_radius=4
                                            )
                                        ]
                                    ),
                                    ft.Text(f"التكلفة: {cost:.2f} TL", size=12, color="#64748B"),
                                    ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.Icon(ft.icons.CIRCLE, size=8, color=status_color),
                                            ft.Text(f"{qty} قطعة ({status_text_val})", size=12, color=status_color)
                                        ]
                                    )
                                ]
                            ),
                            ft.ElevatedButton(
                                "بيع",
                                icon=ft.icons.SHOPPING_BAG_OUTLINED,
                                bgcolor="#16A34A",
                                color=ft.colors.WHITE,
                                on_click=lambda e, vid=v_id, n=name, c=color, s=size, q=qty, cp=cost: show_sale_section(vid, n, c, s, q, cp)
                            )
                        ]
                    )
                )
                stock_list_view.controls.append(card)
        page.update()

    def load_stock():
        nonlocal all_stock_data
        try:
            conn = sqlite3.connect(get_safe_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT id, product_name, color, size, quantity, cost_price FROM variants ORDER BY product_name ASC, color ASC")
            all_stock_data = cursor.fetchall()
            conn.close()
            update_metrics()
            render_stock(all_stock_data)
        except Exception as err:
            show_in_page_alert(f"خطأ في قراءة المخزن: {err}", is_error=True)

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

    # --- حاسبة التسعير ---
    calc_cost_input = ft.TextField(label="التكلفة (TL)", value="140", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, bgcolor=ft.colors.WHITE, dense=True)
    calc_profit_input = ft.TextField(label="الربح المطلوب (TL)", value="100", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, bgcolor=ft.colors.WHITE, dense=True)
    calc_shipping_input = ft.TextField(label="الشحن (TL)", value="35", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, bgcolor=ft.colors.WHITE, dense=True)

    calc_store_price_text = ft.Text("0.00 TL", size=14, weight=ft.FontWeight.BOLD, color="#1D4ED8")
    calc_trendyol_price_text = ft.Text("0.00 TL", size=14, weight=ft.FontWeight.BOLD, color="#EA580C")
    calc_details_text = ft.Text("", size=11, color="#475569")

    def run_pricing_calc(e):
        try:
            cost = float(calc_cost_input.value.replace(",", "."))
            desired_profit = float(calc_profit_input.value.replace(",", "."))
            shipping = float(calc_shipping_input.value.replace(",", "."))
        except ValueError:
            show_in_page_alert("⚠️ يرجى إدخال أرقام صحيحة!", is_error=True)
            return

        store_price = cost + desired_profit
        trendyol_price = (cost + desired_profit + shipping) / (1 - 0.167)
        commission_val = trendyol_price * 0.167

        calc_store_price_text.value = f"{store_price:.2f} TL"
        calc_trendyol_price_text.value = f"{trendyol_price:.2f} TL"
        calc_details_text.value = (
            f"عمولة ترينديول (16.7%): {commission_val:.2f} TL | الشحن: {shipping:.2f} TL | "
            f"التكلفة: {cost:.2f} TL ➔ الصافي: +{desired_profit:.2f} TL"
        )
        page.update()

    pricing_panel = ft.Container(
        visible=False,
        padding=10,
        bgcolor="#FFFBEB",
        border_radius=10,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("🧮 محاكي التسعير وترينديول", size=14, weight=ft.FontWeight.BOLD, color="#B45309"),
                        ft.IconButton(ft.icons.CLOSE, icon_color="#B45309", on_click=lambda e: toggle_pricing_panel())
                    ]
                ),
                ft.Row(
                    spacing=4,
                    controls=[
                        ft.Container(calc_cost_input, expand=True),
                        ft.Container(calc_profit_input, expand=True),
                        ft.Container(calc_shipping_input, expand=True)
                    ]
                ),
                ft.ElevatedButton("⚡ حساب الأسعار", bgcolor="#D97706", color=ft.colors.WHITE, on_click=run_pricing_calc),
                ft.Divider(),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text("سعر البيع بالمحل", size=11, color="#475569"),
                                calc_store_price_text
                            ]
                        ),
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text("سعر Trendyol", size=11, color="#475569"),
                                calc_trendyol_price_text
                            ]
                        )
                    ]
                ),
                calc_details_text
            ]
        )
    )

    def toggle_pricing_panel():
        pricing_panel.visible = not pricing_panel.visible
        page.update()

    # --- تصدير التقارير ---
    def export_excel_report(e):
        try:
            conn = sqlite3.connect(get_safe_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT product_name, color, size, quantity, cost_price, (quantity * cost_price) FROM variants ORDER BY product_name ASC")
            stock_rows = cursor.fetchall()
            cursor.execute("SELECT sale_date, channel, product_name, color, size, quantity, cost_price, sale_price, (quantity * sale_price), deductions, ((quantity * sale_price) - deductions - (quantity * cost_price)) FROM sales ORDER BY id DESC")
            sales_rows = cursor.fetchall()
            conn.close()

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            export_dir = os.path.dirname(get_safe_db_path())
            file_name = os.path.join(export_dir, f"ME_Tekstil_Rapor_{timestamp}.csv")
            with open(file_name, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["=== GUNCEL STOK LISTESI ==="])
                writer.writerow(["Urun", "Renk", "Beden", "Stok Adedi", "Birim Maliyet (TL)", "Toplam Maliyet Tutari (TL)"])
                for r in stock_rows:
                    writer.writerow(r)
                writer.writerow([])
                writer.writerow(["=== SATIS VE KAR GECMISI ==="])
                writer.writerow(["Tarih", "Kanal", "Urun", "Renk", "Beden", "Satilan Adet", "Birim Maliyet", "Satis Fiyati", "Toplam Ciro", "Platform Kesintisi", "Net Kar"])
                for sr in sales_rows:
                    writer.writerow(sr)

            show_in_page_alert(f"✅ تم حفظ التقرير: {os.path.basename(file_name)}")
        except Exception as ex:
            show_in_page_alert(f"⚠️ خطأ أثناء التصدير: {ex}", is_error=True)

    # --- لوحة اللصق الذكي ---
    sample_pantolon = "Zara Krep Pantolon\nMaliyet: 140\nBeden: 34, 36, 38, 40, 42, 44\nsiyah: 7, 7, 14, 14, 7, 7\nlaci: 1, 1, 2, 2, 1, 1\nbordo: 5, 5, 10, 10, 5, 5"
    sample_blouse = "Kare Yaka Bluz\nMaliyet: 95\nBeden: S, M, L, XL, 2XL\nsiyah: 10, 10, 15, 15, 10\npudra: 10, 10, 15, 15, 10\nbeyaz: 10, 10, 15, 15, 10"

    paste_input = ft.TextField(
        label="الصق النص هنا",
        multiline=True,
        min_lines=5,
        max_lines=8,
        value=sample_pantolon,
        border_radius=8,
        bgcolor=ft.colors.WHITE
    )

    def process_smart_paste(e):
        raw = paste_input.value.strip()
        if not raw:
            return

        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        model_name = "urun"
        cost_price = 100.0
        sizes = []
        parsed_items = []

        for line in lines:
            l_low = line.lower()
            if any(k in l_low for k in ["تكلفة", "maliyet", "cost", "fiyat"]):
                m = re.search(r'(\d+(?:[.,]\d+)?)', l_low)
                if m:
                    cost_price = float(m.group(1).replace(",", "."))
            elif any(k in l_low for k in ["مقاس", "beden", "size"]):
                parts = re.split(r'[:=]', line, 1)
                if len(parts) > 1:
                    sizes = [s.strip().upper() for s in re.split(r'[, \t]+', parts[1]) if s.strip()]
            elif ":" not in line and len(line.split()) >= 1 and not any(k in l_low for k in ["stok", "adet", "tl", "toplam"]):
                model_name = line.strip().lower()

        if not sizes:
            if any(w in model_name for w in ["pantolon", "tayt", "بنطلون"]):
                sizes = ["34", "36", "38", "40", "42", "44"]
            else:
                sizes = ["S", "M", "L", "XL", "2XL"]

        for line in lines:
            if ":" in line:
                c_name, q_str = line.split(":", 1)
                c_name = c_name.strip().lower()
                
                if any(w in c_name for w in ["maliyet", "beden", "size", "تكلفة", "مقاس"]):
                    continue

                raw_nums = re.findall(r'\d+', q_str)
                if raw_nums:
                    quantities = [int(n) for n in raw_nums]
                    for i, q in enumerate(quantities):
                        s = sizes[i] if i < len(sizes) else f"T{i+1}"
                        parsed_items.append((model_name, c_name, s, q, cost_price))

        if not parsed_items:
            show_in_page_alert("⚠️ تعذر استخراج البيانات، تأكد من وجود النقطتين :", is_error=True)
            return

        conn = sqlite3.connect(get_safe_db_path())
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

        smart_paste_panel.visible = False
        show_in_page_alert(f"✅ تمت إضافة {total_added} قطعة في المخزن!")
        load_stock()

    smart_paste_panel = ft.Container(
        visible=False,
        padding=10,
        bgcolor="#EEF2FF",
        border_radius=10,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("📋 اللصق الذكي", size=14, weight=ft.FontWeight.BOLD, color="#3730A3"),
                        ft.IconButton(ft.icons.CLOSE, icon_color="#4338CA", on_click=lambda e: toggle_smart_paste())
                    ]
                ),
                ft.Row(
                    spacing=4,
                    controls=[
                        ft.ElevatedButton("قالب بناطيل", on_click=lambda e: setattr(paste_input, 'value', sample_pantolon) or page.update(), bgcolor="#4338CA", color=ft.colors.WHITE),
                        ft.ElevatedButton("قالب بلوزات", on_click=lambda e: setattr(paste_input, 'value', sample_blouse) or page.update(), bgcolor="#4338CA", color=ft.colors.WHITE)
                    ]
                ),
                paste_input,
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    spacing=6,
                    controls=[
                        ft.TextButton("إلغاء", on_click=lambda e: toggle_smart_paste()),
                        ft.ElevatedButton("⚡ حفظ في المخزن", bgcolor="#4F46E5", color=ft.colors.WHITE, on_click=process_smart_paste)
                    ]
                )
            ]
        )
    )

    def toggle_smart_paste():
        smart_paste_panel.visible = not smart_paste_panel.visible
        page.update()

    # --- لوحة البيع ---
    sale_panel_title = ft.Text("", size=13, weight=ft.FontWeight.BOLD, color="#0F172A")
    sale_qty_input = ft.TextField(label="الكمية", value="1", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, bgcolor=ft.colors.WHITE, dense=True)
    sale_price_input = ft.TextField(label="سعر البيع (TL)", value="250", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, bgcolor=ft.colors.WHITE, dense=True)
    sale_channel_dropdown = ft.Dropdown(
        label="القناة",
        value="Mağaza",
        border_radius=8,
        bgcolor=ft.colors.WHITE,
        options=[
            ft.dropdown.Option("Mağaza"),
            ft.dropdown.Option("Trendyol"),
            ft.dropdown.Option("Toptan")
        ]
    )
    current_sale_context = {}

    def show_sale_section(v_id, name, color, size, max_qty, cost_price):
        nonlocal current_sale_context
        current_sale_context = {
            "v_id": v_id, "name": name, "color": color, "size": size,
            "max_qty": max_qty, "cost_price": cost_price
        }
        sale_panel_title.value = f"🛍️ بيع: {name.title()} ({color.title()} - {size}) | المتوفر: {max_qty}"
        sale_panel.visible = True
        page.update()

    def confirm_sale_action(e):
        try:
            qty = int(sale_qty_input.value)
            price = float(sale_price_input.value)
            channel = sale_channel_dropdown.value
        except ValueError:
            show_in_page_alert("⚠️ أدخل أرقام صحيحة!", is_error=True)
            return

        max_qty = current_sale_context.get("max_qty", 0)
        if qty <= 0 or qty > max_qty:
            show_in_page_alert(f"⚠️ الكم
