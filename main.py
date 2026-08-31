import sqlite3
import datetime
import flet as ft

# --- إعداد قاعدة البيانات ---
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
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 12
    page.scroll = ft.ScrollMode.AUTO
    page.bgcolor = "#F8FAFC"

    # عناصر واجهة المستخدم
    stat_total_stock = ft.Text("0", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_900)
    stat_today_sales = ft.Text("0", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO_900)
    stat_today_profit = ft.Text("0.00 TL", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_900)

    stock_list_view = ft.Column(spacing=8)
    search_input = ft.TextField(
        hint_text="ابحث عن موديل، لون، مقاس...",
        prefix_icon=ft.icons.SEARCH,
        border_radius=12,
        bgcolor=ft.colors.WHITE,
        dense=True,
        on_change=lambda e: filter_stock(e.control.value)
    )

    all_stock_data = []

    # --- تحديث المؤشرات العلوية ---
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

    # --- تحديث قائمة المخزون ---
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
                            ft.Icon(ft.icons.INVENTORY_2_OUTLINED, size=48, color=ft.colors.GREY_400),
                            ft.Text("لا توجد منتجات مطابقة في المخزن", color=ft.colors.GREY_600, size=15)
                        ]
                    ),
                    alignment=ft.alignment.center,
                    padding=30
                )
            )
        else:
            for item in items:
                v_id, name, color, size, qty, cost = item
                status_color = ft.colors.GREEN_600 if qty > 3 else (ft.colors.ORANGE_600 if qty > 0 else ft.colors.RED_600)
                status_text = "متوفر" if qty > 3 else ("قليل" if qty > 0 else "نفد")

                card = ft.Container(
                    padding=14,
                    border_radius=14,
                    bgcolor=ft.colors.WHITE,
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
                                            ft.Text(f"{name.title()} ({color.title()})", size=16, weight=ft.FontWeight.BOLD, color="#1E293B"),
                                            ft.Container(
                                                content=ft.Text(size, size=12, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_800),
                                                bgcolor=ft.colors.BLUE_50,
                                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                                border_radius=6
                                            )
                                        ]
                                    ),
                                    ft.Text(f"التكلفة: {cost:.2f} TL", size=13, color="#64748B"),
                                    ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.Icon(ft.icons.CIRCLE, size=9, color=status_color),
                                            ft.Text(f"{qty} قطعة ({status_text})", size=13, weight=ft.FontWeight.W_500, color=status_color)
                                        ]
                                    )
                                ]
                            ),
                            ft.ElevatedButton(
                                "بيع",
                                icon=ft.icons.SHOPPING_BAG_OUTLINED,
                                bgcolor=ft.colors.GREEN_600,
                                color=ft.colors.WHITE,
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

    # --- نافذة تسجيل البيع ---
    def open_sale_dialog(variant_id, name, color, size, max_qty, cost_price):
        qty_input = ft.TextField(label="الكمية", value="1", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8)
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
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ يرجى إدخال أرقام صحيحة!"), bgcolor=ft.colors.RED_700)
                page.snack_bar.open = True
                page.update()
                return

            if sale_qty <= 0 or sale_qty > max_qty:
                page.snack_bar = ft.SnackBar(ft.Text(f"⚠️ الكمية غير متاحة! المتوفر في المخزن: {max_qty}"), bgcolor=ft.colors.RED_700)
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
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ تم تسجيل بيع {sale_qty} قطعة بنجاح!"), bgcolor=ft.colors.GREEN_700)
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
                ft.ElevatedButton("تأكيد وخصم", on_click=confirm_sale, bgcolor=ft.colors.GREEN_600, color=ft.colors.WHITE)
            ]
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

    # --- نافذة إضافة بضاعة جديدة ---
    def open_add_dialog(e):
        name_input = ft.TextField(label="اسم الموديل (Örn: Pantolon / Atlet)", border_radius=8)
        color_input = ft.TextField(label="اللون (Örn: Siyah / Sarı / Pudra)", border_radius=8)
        size_input = ft.TextField(label="المقاسات (Örn: S,M,L,XL أو 34,36,38)", border_radius=8)
        qty_input = ft.TextField(label="الكمية لكل مقاس", value="10", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8)
        cost_input = ft.TextField(label="سعر التكلفة (TL)", value="95", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8)

        def save_new_stock(ev):
            p_name = name_input.value.strip().lower()
            p_color = color_input.value.strip().lower()
            raw_sizes = size_input.value.replace(".", ",").replace(" ", ",").split(",")
            sizes = [s.strip().upper() for s in raw_sizes if s.strip()]

            if not p_name or not p_color or not sizes:
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ يرجى تعبئة كافة الحقول!"), bgcolor=ft.colors.RED_700)
                page.snack_bar.open = True
                page.update()
                return

            try:
                qty = int(qty_input.value)
                cost = float(cost_input.value)
            except ValueError:
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ يرجى إدخال أرقام صحيحة للكمية والتكلفة!"), bgcolor=ft.colors.RED_700)
                page.snack_bar.open = True
                page.update()
                return

            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            for s in sizes:
                cursor.execute("""
                    INSERT INTO variants (product_name, color, size, quantity, cost_price)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(product_name, color, size) DO UPDATE SET
                    quantity = quantity + excluded.quantity,
                    cost_price = excluded.cost_price
                """, (p_name, p_color, s, qty, cost))
            conn.commit()
            conn.close()

            add_dialog.open = False
            page.snack_bar = ft.SnackBar(ft.Text("✅ تم حفظ البضاعة بنجاح!"), bgcolor=ft.colors.GREEN_700)
            page.snack_bar.open = True
            load_stock()

        def close_add(ev):
            add_dialog.open = False
            page.update()

        add_dialog = ft.AlertDialog(
            title=ft.Text("➕ إضافة بضاعة جديدة للمخزن"),
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[
                    name_input,
                    color_input,
                    size_input,
                    qty_input,
                    cost_input
                ]
            ),
            actions=[
                ft.TextButton("إلغاء", on_click=close_add),
                ft.ElevatedButton("حفظ في المخزن", on_click=save_new_stock, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE)
            ]
        )

        page.dialog = add_dialog
        add_dialog.open = True
        page.update()

    # --- شريط التطبيق العلوي ---
    page.appbar = ft.AppBar(
        title=ft.Text("M&E Tekstil ERP", weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
        center_title=True,
        bgcolor="#1E293B",
        actions=[
            ft.IconButton(ft.icons.REFRESH, tooltip="تحديث", icon_color=ft.colors.WHITE, on_click=lambda e: load_stock())
        ]
    )

    # بطاقات لوحة التحكم العلوية (Dashboard KPI Cards)
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
                            ft.Text(title, size=12, color="#475569", weight=ft.FontWeight.W_500),
                            ft.Icon(icon, size=18, color="#475569")
                        ]
                    ),
                    value_widget
                ]
            )
        )

    dashboard_row = ft.Row(
        spacing=8,
        controls=[
            kpi_card("إجمالي المخزن", stat_total_stock, ft.icons.INVENTORY, "#EFF6FF"),
            kpi_card("مبيعات اليوم", stat_today_sales, ft.icons.SHOPPING_CART, "#EEF2FF"),
            kpi_card("أرباح اليوم", stat_today_profit, ft.icons.ATTACH_MONEY, "#F0FDF4"),
        ]
    )

    # الزر العائم لإضافة البضائع
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.icons.ADD,
        bgcolor=ft.colors.BLUE_700,
        content=ft.Icon(ft.icons.ADD, color=ft.colors.WHITE),
        on_click=open_add_dialog,
        tooltip="إضافة بضاعة جديدة"
    )

    page.add(
        dashboard_row,
        ft.Container(height=6),
        search_input,
        ft.Container(height=6),
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("📦 قائمة المخزون", size=16, weight=ft.FontWeight.BOLD, color="#1E293B"),
                ft.TextButton("➕ إضافة سريعة", on_click=open_add_dialog)
            ]
        ),
        stock_list_view
    )

    load_stock()

ft.app(target=main)
                
