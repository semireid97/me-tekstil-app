import json
import datetime
import re
import os
import csv
import urllib.request
import flet as ft

# رابط Google Apps Script الخاص بك
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxm977X_VWNWq3mICJlNTml1W1MbnkkwHvmwIWXpNbChP3gfPLfiTqGxuifV2_k7r0aVA/exec"

def get_data_dir():
    paths = [
        os.environ.get("FLET_APP_STORAGE_DATA"),
        os.environ.get("HOME"),
        os.path.expanduser("~"),
        "."
    ]
    for p in paths:
        if p and os.path.exists(p):
            return p
    return "."

def get_db_file():
    return os.path.join(get_data_dir(), "erp_store_data.json")

def load_db():
    fpath = get_db_file()
    default_data = {"variants": [], "sales": []}
    if not os.path.exists(fpath):
        save_db(default_data)
        return default_data
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_data

def save_db(data):
    try:
        with open(get_db_file(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def main(page: ft.Page):
    page.title = "M&E Tekstil ERP"
    page.padding = 10
    page.scroll = ft.ScrollMode.AUTO
    page.bgcolor = "#F8FAFC"

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

    def update_metrics(db_data):
        try:
            tot_stock = sum(item.get("quantity", 0) for item in db_data.get("variants", []))
            stat_total_stock.value = f"{tot_stock} قطعة"

            today_date = datetime.datetime.now().strftime("%Y-%m-%d")
            today_sales = [
                s for s in db_data.get("sales", [])
                if s.get("sale_date", "").startswith(today_date)
            ]
            t_qty = sum(s.get("quantity", 0) for s in today_sales)
            t_profit = sum(
                ((s.get("sale_price", 0) - s.get("cost_price", 0)) * s.get("quantity", 0)) - s.get("deductions", 0)
                for s in today_sales
            )
            stat_today_sales.value = f"{t_qty} قطعة"
            stat_today_profit.value = f"+{t_profit:.2f} TL"
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
                v_id = item["id"]
                name = item["product_name"]
                color = item["color"]
                size = item["size"]
                qty = item["quantity"]
                cost = item["cost_price"]

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
            db_data = load_db()
            all_stock_data = sorted(db_data.get("variants", []), key=lambda x: (x.get("product_name", ""), x.get("color", "")))
            update_metrics(db_data)
            render_stock(all_stock_data)
        except Exception as err:
            show_in_page_alert(f"خطأ: {err}", is_error=True)

    def filter_stock(query):
        q = query.strip().lower()
        if not q:
            render_stock(all_stock_data)
        else:
            filtered = [
                it for it in all_stock_data
                if q in it.get("product_name", "").lower() or q in it.get("color", "").lower() or q in it.get("size", "").lower()
            ]
            render_stock(filtered)

    # --- مزامنة Google Sheets ---
    def sync_to_google_sheets(e):
        show_in_page_alert("⏳ جاري المزامنة مع Google Sheets...")
        try:
            db_data = load_db()
            payload = {
                "action": "sync_all",
                "variants": db_data.get("variants", []),
                "sales": []
            }

            for s in db_data.get("sales", []):
                net_p = (s.get("quantity", 0) * s.get("sale_price", 0)) - s.get("deductions", 0) - (s.get("quantity", 0) * s.get("cost_price", 0))
                payload["sales"].append({
                    "sale_date": s.get("sale_date"),
                    "channel": s.get("channel"),
                    "product_name": s.get("product_name"),
                    "color": s.get("color"),
                    "size": s.get("size"),
                    "quantity": s.get("quantity"),
                    "sale_price": s.get("sale_price"),
                    "net_profit": net_p
                })

            req = urllib.request.Request(
                GOOGLE_SCRIPT_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                res = json.loads(response.read().decode("utf-8"))
                if res.get("status") == "success":
                    show_in_page_alert("☁️ تمت المزامنة مع Google Sheets بنجاح!")
                else:
                    show_in_page_alert("⚠️ تم الاتصال ولكن تعذر تحديث الجدول", is_error=True)

        except Exception as ex:
            show_in_page_alert(f"⚠️ تعذر الاتصال بالسحاب: {ex}", is_error=True)

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
            db_data = load_db()
            stock_rows = [
                [it["product_name"], it["color"], it["size"], it["quantity"], it["cost_price"], it["quantity"] * it["cost_price"]]
                for it in db_data.get("variants", [])
            ]
            sales_rows = [
                [s.get("sale_date"), s.get("channel"), s.get("product_name"), s.get("color"), s.get("size"),
                 s.get("quantity"), s.get("cost_price"), s.get("sale_price"),
                 s.get("quantity", 0) * s.get("sale_price", 0), s.get("deductions", 0),
                 ((s.get("quantity", 0) * s.get("sale_price", 0)) - s.get("deductions", 0) - (s.get("quantity", 0) * s.get("cost_price", 0)))]
                for s in reversed(db_data.get("sales", []))
            ]

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            export_dir = get_data_dir()
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

    # --- اللصق الذكي ---
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
                        parsed_items.append({"name": model_name, "color": c_name, "size": s, "qty": q, "cost": cost_price})

        if not parsed_items:
            show_in_page_alert("⚠️ تعذر استخراج البيانات، تأكد من وضع النقطتين :", is_error=True)
            return

        db_data = load_db()
        variants = db_data.get("variants", [])
        total_added = 0

        for item in parsed_items:
            total_added += item["qty"]
            found = False
            for v in variants:
                if v["product_name"] == item["name"] and v["color"] == item["color"] and v["size"] == item["size"]:
                    v["quantity"] += item["qty"]
                    v["cost_price"] = item["cost"]
                    found = True
                    break
            if not found:
                new_id = (max([v["id"] for v in variants], default=0)) + 1
                variants.append({
                    "id": new_id,
                    "product_name": item["name"],
                    "color": item["color"],
                    "size": item["size"],
                    "quantity": item["qty"],
                    "cost_price": item["cost"]
                })

        db_data["variants"] = variants
        save_db(db_data)

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

    # --- تسجيل البيع ---
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
            show_in_page_alert(f"⚠️ الكمية غير صالحة! المتوفر: {max_qty}", is_error=True)
            return

        v_id = current_sale_context["v_id"]
        name = current_sale_context["name"]
        color = current_sale_context["color"]
        size = current_sale_context["size"]
        cost = current_sale_context["cost_price"]
        deductions = (price * qty * 0.167) if channel == "Trendyol" else 0.0

        db_data = load_db()
        for v in db_data.get("variants", []):
            if v["id"] == v_id:
                v["quantity"] -= qty
                break

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db_data.setdefault("sales", []).append({
            "product_name": name,
            "color": color,
            "size": size,
            "quantity": qty,
            "cost_price": cost,
            "sale_price": price,
            "channel": channel,
            "deductions": deductions,
            "sale_date": now_str
        })

        save_db(db_data)
        sale_panel.visible = False
        show_in_page_alert(f"✅ تم تسجيل بيع {qty} قطعة!")
        load_stock()

    sale_panel = ft.Container(
        visible=False,
        padding=10,
        bgcolor="#DCFCE7",
        border_radius=10,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        sale_panel_title,
                        ft.IconButton(ft.icons.CLOSE, icon_color="#15803D", on_click=lambda e: setattr(sale_panel, 'visible', False) or page.update())
                    ]
                ),
                sale_qty_input,
                sale_price_input,
                sale_channel_dropdown,
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    spacing=6,
                    controls=[
                        ft.TextButton("إلغاء", on_click=lambda e: setattr(sale_panel, 'visible', False) or page.update()),
                        ft.ElevatedButton("تأكيد وخصم", bgcolor="#16A34A", color=ft.colors.WHITE, on_click=confirm_sale_action)
                    ]
                )
            ]
        )
    )

    page.appbar = ft.AppBar(
        title=ft.Text("M&E Tekstil ERP", weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
        center_title=True,
        bgcolor="#0F172A",
        actions=[
            ft.IconButton(ft.icons.REFRESH, tooltip="تحديث", icon_color=ft.colors.WHITE, on_click=lambda e: load_stock())
        ]
    )

    def kpi_card(title, value_widget, icon, bg_color):
        return ft.Container(
            expand=True,
            padding=8,
            border_radius=8,
            bgcolor=bg_color,
            content=ft.Column(
                spacing=2,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(title, size=10, color="#475569", weight=ft.FontWeight.W_500),
                            ft.Icon(icon, size=14, color="#475569")
                        ]
                    ),
                    value_widget
                ]
            )
        )

    dashboard_row = ft.Row(
        spacing=6,
        controls=[
            kpi_card("المخزن", stat_total_stock, ft.icons.INVENTORY_2, "#EFF6FF"),
            kpi_card("المبيعات", stat_today_sales, ft.icons.SHOPPING_BAG, "#EEF2FF"),
            kpi_card("الأرباح", stat_today_profit, ft.icons.ATTACH_MONEY, "#F0FDF4"),
        ]
    )

    action_buttons_row = ft.Row(
        spacing=4,
        controls=[
            ft.ElevatedButton("📋 لصق ذكي", icon=ft.icons.PASTE, bgcolor="#4F46E5", color=ft.colors.WHITE, on_click=lambda e: toggle_smart_paste()),
            ft.ElevatedButton("🧮 حاسبة", icon=ft.icons.CALCULATE, bgcolor="#D97706", color=ft.colors.WHITE, on_click=lambda e: toggle_pricing_panel()),
            ft.ElevatedButton("📥 تصدير", icon=ft.icons.DOWNLOAD, bgcolor="#059669", color=ft.colors.WHITE, on_click=export_excel_report),
            ft.ElevatedButton("☁️ مزامنة", icon=ft.icons.SYNC, bgcolor="#0284C7", color=ft.colors.WHITE, on_click=sync_to_google_sheets),
        ]
    )

    search_input = ft.TextField(
        hint_text="ابحث عن موديل، لون، مقاس...",
        prefix_icon=ft.icons.SEARCH,
        border_radius=8,
        bgcolor=ft.colors.WHITE,
        dense=True,
        on_change=lambda e: filter_stock(e.control.value)
    )

    page.add(
        status_banner,
        dashboard_row,
        ft.Container(height=2),
        action_buttons_row,
        smart_paste_panel,
        pricing_panel,
        sale_panel,
        ft.Container(height=2),
        search_input,
        ft.Container(height=2),
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("📦 المخزون الحالي", size=14, weight=ft.FontWeight.BOLD, color="#0F172A"),
            ]
        ),
        stock_list_view
    )

    page.update()
    load_stock()

ft.app(target=main)
