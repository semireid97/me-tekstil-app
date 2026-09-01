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

    status_banner = ft.Container(visible=False, padding=10, border_radius=8)
    status_text = ft.Text("", color="#FFFFFF", weight=ft.FontWeight.BOLD)
    status_banner.content = status_text

    def show_in_page_alert(msg, is_error=False):
        status_banner.bgcolor = "#DC2626" if is_error else "#16A34A"
        status_text.value = msg
        status_banner.visible = True
        page.update()

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
                status_text_val = "متوفر" if qty > 3 else ("قليل" if qty > 0 else "نفد")

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
                                            ft.Text(f"{qty} قطعة ({status_text_val})", size=13, weight=ft.FontWeight.W_500, color=status_color)
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
                                on_click=lambda e, vid=v_id, n=name, c=color, s=size, q=qty, cp=cost: show_sale_section(vid, n, c, s, q, cp)
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

    # --- نماذج اللصق الجاهزة ---
    sample_pantolon = (
        "Zara Krep Pantolon\n"
        "Maliyet: 140\n"
        "Beden: 34, 36, 38, 40, 42, 44\n"
        "siyah: 7, 7, 14, 14, 7, 7\n"
        "laci: 1, 1, 2, 2, 1, 1\n"
        "bordo: 5, 5, 10, 10, 5, 5"
    )

    sample_blouse = (
        "Kare Yaka Bluz\n"
        "Maliyet: 95\n"
        "Beden: S, M, L, XL, 2XL\n"
        "siyah: 10, 10, 15, 15, 10\n"
        "pudra: 10, 10, 15, 15, 10\n"
        "beyaz: 10, 10, 15, 15, 10"
    )

    paste_input = ft.TextField(
        label="الصق النص أو جدول الإكسل هنا",
        multiline=True,
        min_lines=6,
        max_lines=9,
        value=sample_pantolon,
        border_radius=8,
        bgcolor="#FFFFFF"
    )

    def set_pantolon_template(e):
        paste_input.value = sample_pantolon
        page.update()

    def set_blouse_template(e):
        paste_input.value = sample_blouse
        page.update()

    def process_smart_paste(e):
        raw = paste_input.value.strip()
        if not raw:
            return

        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        model_name = "urun"
        cost_price = 100.0
        sizes = []
        parsed_items = []

        # قراءة أولية لتحديد اسم الموديل والتكلفة والمقاسات الصريحة
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

        # إذا لم يتم تحديد مقاسات بشكل صريح، نحددها تلقائياً بناءً على اسم الموديل
        if not sizes:
            if any(w in model_name for w in ["pantolon", "tayt", "بنطلون"]):
                sizes = ["34", "36", "38", "40", "42", "44"]
            else:
                sizes = ["S", "M", "L", "XL", "2XL"]

        # استخراج الألوان والكميات
        for line in lines:
            if ":" in line:
                c_name, q_str = line.split(":", 1)
                c_name = c_name.strip().lower()
                
                # تخطي أسطر التعريفات
                if any(w in c_name for w in ["maliyet", "beden", "size", "تكلفة", "مقاس"]):
                    continue

                raw_nums = re.findall(r'\d+', q_str)
                if raw_nums:
                    quantities = [int(n) for n in raw_nums]
                    for i, q in enumerate(quantities):
                        if i < len(sizes):
                            s = sizes[i]
                        else:
                            s = f"T{i+1}"
                        parsed_items.append((model_name, c_name, s, q, cost_price))

        if not parsed_items:
            show_in_page_alert("⚠️ تعذر استخراج البيانات، تأكد من وضع اسم اللون ونقطتين : متبوعة بالأرقام", is_error=True)
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

        smart_paste_panel.visible = False
        show_in_page_alert(f"✅ تم إضافة {total_added} قطعة في المخزن ({model_name.title()}) بنجاح!")
        load_stock()

    smart_paste_panel = ft.Container(
        visible=False,
        padding=14,
        bgcolor="#EEF2FF",
        border_radius=12,
        border=ft.border.all(1, "#C7D2FE"),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("📋 صندوق اللصق الذكي", size=16, weight=ft.FontWeight.BOLD, color="#3730A3"),
                        ft.IconButton(ft.Icons.CLOSE, icon_color="#4338CA", on_click=lambda e: toggle_smart_paste())
                    ]
                ),
                ft.Row(
                    spacing=6,
                    controls=[
                        ft.ElevatedButton("👖 قالب بناطيل (34-44)", on_click=set_pantolon_template, bgcolor="#4338CA", color="#FFFFFF"),
                        ft.ElevatedButton("👕 قالب بلوز/شورت (S-2XL)", on_click=set_blouse_template, bgcolor="#4338CA", color="#FFFFFF")
                    ]
                ),
                paste_input,
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                    controls=[
                        ft.TextButton("إلغاء", on_click=lambda e: toggle_smart_paste()),
                        ft.ElevatedButton("⚡ معالجة وحفظ في المخزن", bgcolor="#4F46E5", color="#FFFFFF", on_click=process_smart_paste)
                    ]
                )
            ]
        )
    )

    def toggle_smart_paste():
        smart_paste_panel.visible = not smart_paste_panel.visible
        page.update()

    # --- لوحة البيع المدمجة داخل الصفحة ---
    sale_panel_title = ft.Text("", size=15, weight=ft.FontWeight.BOLD, color="#0F172A")
    sale_qty_input = ft.TextField(label="الكمية المباعة", value="1", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, bgcolor="#FFFFFF")
    sale_price_input = ft.TextField(label="سعر البيع للقطعة (TL)", value="250", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, bgcolor="#FFFFFF")
    sale_channel_dropdown = ft.Dropdown(
        label="منصة البيع",
        value="Mağaza",
        border_radius=8,
        bgcolor="#FFFFFF",
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
        sale_panel_title.value = f"🛍️ تسجيل بيع: {name.title()} ({color.title()} - {size}) | المتوفر: {max_qty}"
        sale_panel.visible = True
        page.update()

    def confirm_sale_action(e):
        try:
            qty = int(sale_qty_input.value)
            price = float(sale_price_input.value)
            channel = sale_channel_dropdown.value
        except ValueError:
            show_in_page_alert("⚠️ يرجى إدخال أرقام صحيحة!", is_error=True)
            return

        max_qty = current_sale_context.get("max_qty", 0)
        if qty <= 0 or qty > max_qty:
            show_in_page_alert(f"⚠️ الكمية غير صالحة! المتوفر: {max_qty}", is_error=True)
            return

        v_id = current_sale_context["v_id"]
        name = current_sale_context["name"]
        color = current_sale_context["color"]
        size = current_sale_context["size"]
        cost = current_sale_context["cost_price"]

        deductions = (price * qty * 0.167) if channel == "Trendyol" else 0.0

        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE variants SET quantity = quantity - ? WHERE id = ?", (qty, v_id))
        cursor.execute("""
            INSERT INTO sales (product_name, color, size, quantity, cost_price, sale_price, channel, deductions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, color, size, qty, cost, price, channel, deductions))
        conn.commit()
        conn.close()

        sale_panel.visible = False
        show_in_page_alert(f"✅ تم تسجيل بيع {qty} قطعة بنجاح!")
        load_stock()

    sale_panel = ft.Container(
        visible=False,
        padding=14,
        bgcolor="#DCFCE7",
        border_radius=12,
        border=ft.border.all(1, "#86EFAC"),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        sale_panel_title,
                        ft.IconButton(ft.Icons.CLOSE, icon_color="#15803D", on_click=lambda e: setattr(sale_panel, 'visible', False) or page.update())
                    ]
                ),
                sale_qty_input,
                sale_price_input,
                sale_channel_dropdown,
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                    controls=[
                        ft.TextButton("إلغاء", on_click=lambda e: setattr(sale_panel, 'visible', False) or page.update()),
                        ft.ElevatedButton("تأكيد وخصم من المخزن", bgcolor="#16A34A", color="#FFFFFF", on_click=confirm_sale_action)
                    ]
                )
            ]
        )
    )

    # --- شريط التطبيق والمؤشرات ---
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

    search_input = ft.TextField(
        hint_text="ابحث عن موديل، لون، مقاس...",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=12,
        bgcolor="#FFFFFF",
        dense=True,
        on_change=lambda e: filter_stock(e.control.value)
    )

    page.add(
        status_banner,
        dashboard_row,
        ft.Container(height=4),
        ft.ElevatedButton(
            "📋 فتح صندوق اللصق الذكي (Smart Paste)",
            icon=ft.Icons.PASTE,
            bgcolor="#4F46E5",
            color="#FFFFFF",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=lambda e: toggle_smart_paste()
        ),
        smart_paste_panel,
        sale_panel,
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
                        
