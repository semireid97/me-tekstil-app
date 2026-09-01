import json
import datetime
import os
import csv
import urllib.request
import flet as ft

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxm977X_VWNWq3mICJlNTml1W1MbnkkwHvmwIWXpNbChP3gfPLfiTqGxuifV2_k7r0aVA/exec"

# التخزين الداخلي المباشر
DATA_STORE = {
    "variants": [
        {"id": 1, "product_name": "zara krep pantolon", "color": "siyah", "size": "38", "quantity": 14, "cost_price": 140.0},
        {"id": 2, "product_name": "zara krep pantolon", "color": "laci", "size": "36", "quantity": 8, "cost_price": 140.0},
        {"id": 3, "product_name": "kare yaka bluz", "color": "beyaz", "size": "M", "quantity": 12, "cost_price": 95.0}
    ],
    "sales": []
}

def get_file_path():
    base = os.environ.get("FLET_APP_STORAGE_DATA") or os.environ.get("HOME") or "."
    return os.path.join(base, "me_data.json")

def load_data():
    global DATA_STORE
    fp = get_file_path()
    if os.path.exists(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                DATA_STORE = json.load(f)
        except Exception:
            pass
    return DATA_STORE

def save_data():
    try:
        with open(get_file_path(), "w", encoding="utf-8") as f:
            json.dump(DATA_STORE, f, ensure_ascii=False)
    except Exception:
        pass

def main(page: ft.Page):
    page.title = "M&E Tekstil ERP"
    page.padding = 10
    page.scroll = ft.ScrollMode.AUTO
    page.bgcolor = "#F8FAFC"

    load_data()

    stat_total_stock = ft.Text("0", size=15, weight=ft.FontWeight.BOLD, color="#1E3A8A")
    stat_today_sales = ft.Text("0", size=15, weight=ft.FontWeight.BOLD, color="#312E81")
    stat_today_profit = ft.Text("0.00 TL", size=15, weight=ft.FontWeight.BOLD, color="#14532D")

    stock_list_view = ft.Column(spacing=8)
    status_banner = ft.Container(visible=False, padding=10, border_radius=8)
    status_text = ft.Text("", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD)
    status_banner.content = status_text

    def show_alert(msg, is_error=False):
        status_banner.bgcolor = "#DC2626" if is_error else "#16A34A"
        status_text.value = msg
        status_banner.visible = True
        page.update()

    def update_metrics():
        tot_qty = sum(v.get("quantity", 0) for v in DATA_STORE["variants"])
        stat_total_stock.value = f"{tot_qty} قطعة"

        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        t_sales = [s for s in DATA_STORE["sales"] if s.get("sale_date", "").startswith(today_str)]
        t_qty = sum(s.get("quantity", 0) for s in t_sales)
        t_profit = sum(
            ((s.get("sale_price", 0) - s.get("cost_price", 0)) * s.get("quantity", 0)) - s.get("deductions", 0)
            for s in t_sales
        )

        stat_today_sales.value = f"{t_qty} قطعة"
        stat_today_profit.value = f"+{t_profit:.2f} TL"

    def render_stock(items=None):
        if items is None:
            items = DATA_STORE["variants"]
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
                                on_click=lambda e, vid=v_id, n=name, c=color, s=size, q=qty, cp=cost: show_sale_modal(vid, n, c, s, q, cp)
                            )
                        ]
                    )
                )
                stock_list_view.controls.append(card)
        update_metrics()
        page.update()

    # --- حاسبة الأسعار ---
    calc_cost = ft.TextField(label="التكلفة", value="140", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    calc_profit = ft.TextField(label="الربح المطلوب", value="100", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    calc_shipping = ft.TextField(label="الشحن", value="35", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    calc_res_store = ft.Text("0.00 TL", size=14, weight=ft.FontWeight.BOLD, color="#1D4ED8")
    calc_res_trendyol = ft.Text("0.00 TL", size=14, weight=ft.FontWeight.BOLD, color="#EA580C")
    calc_info = ft.Text("", size=11, color="#475569")

    def run_calc(e):
        try:
            c = float(calc_cost.value.replace(",", "."))
            p = float(calc_profit.value.replace(",", "."))
            s = float(calc_shipping.value.replace(",", "."))
        except Exception:
            show_alert("أدخل أرقام صحيحة", is_error=True)
            return

        st_p = c + p
        tr_p = (c + p + s) / (1 - 0.167)
        comm = tr_p * 0.167

        calc_res_store.value = f"{st_p:.2f} TL"
        calc_res_trendyol.value = f"{tr_p:.2f} TL"
        calc_info.value = f"عمولة ترينديول: {comm:.2f} TL | الشحن: {s:.2f} TL ➔ الصافي: +{p:.2f} TL"
        page.update()

    calc_panel = ft.Container(
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
                        ft.IconButton(ft.icons.CLOSE, icon_color="#B45309", on_click=lambda e: setattr(calc_panel, 'visible', False) or page.update())
                    ]
                ),
                ft.Row(spacing=4, controls=[ft.Container(calc_cost, expand=True), ft.Container(calc_profit, expand=True), ft.Container(calc_shipping, expand=True)]),
                ft.ElevatedButton("⚡ حساب", bgcolor="#D97706", color=ft.colors.WHITE, on_click=run_calc),
                ft.Divider(),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND, controls=[
                    ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("سعر المتجر", size=11), calc_res_store]),
                    ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("سعر Trendyol", size=11), calc_res_trendyol])
                ]),
                calc_info
            ]
        )
    )

    # --- المزامنة مع Google Sheets ---
    def sync_sheets(e):
        show_alert("⏳ جاري المزامنة...")
        try:
            payload = {
                "action": "sync_all",
                "variants": DATA_STORE["variants"],
                "sales": DATA_STORE["sales"]
            }
            req = urllib.request.Request(
                GOOGLE_SCRIPT_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as res:
                r = json.loads(res.read().decode("utf-8"))
                if r.get("status") == "success":
                    show_alert("☁️ تمت المزامنة مع Google Sheets بنجاح!")
                else:
                    show_alert("⚠️ تم الاتصال وتعذر التحديث", is_error=True)
        except Exception as ex:
            show_alert(f"⚠️ خطأ مزامنة: {ex}", is_error=True)

    # --- تصدير CSV ---
    def export_csv(e):
        try:
            base = os.environ.get("FLET_APP_STORAGE_DATA") or "."
            fn = os.path.join(base, "ME_Tekstil_Report.csv")
            with open(fn, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Urun", "Renk", "Beden", "Adet", "Maliyet"])
                for v in DATA_STORE["variants"]:
                    w.writerow([v["product_name"], v["color"], v["size"], v["quantity"], v["cost_price"]])
            show_alert("✅ تم إنشاء ملف التقرير بنجاح")
        except Exception as ex:
            show_alert(f"⚠️ خطأ تصدير: {ex}", is_error=True)

    # --- اللصق السريع ---
    paste_field = ft.TextField(
        multiline=True,
        min_lines=4,
        max_lines=6,
        value="Zara Pantolon\nMaliyet: 140\nBeden: 36, 38, 40\nsiyah: 5, 10, 5",
        bgcolor=ft.colors.WHITE
    )

    def process_paste(e):
        raw = paste_field.value.strip().split("\n")
        if not raw:
            return
        m_name = raw[0].strip().lower()
        cost = 100.0
        sizes = ["36", "38", "40", "42"]

        for l in raw:
            if "maliyet" in l.lower() or "تكلفة" in l:
                digits = [float(s) for s in l.replace(":", " ").split() if s.replace(".", "", 1).isdigit()]
                if digits:
                    cost = digits[0]
            elif "beden" in l.lower() or "مقاس" in l:
                if ":" in l:
                    sizes = [s.strip().upper() for s in l.split(":", 1)[1].replace(",", " ").split() if s.strip()]

        for l in raw:
            if ":" in l and not any(k in l.lower() for k in ["maliyet", "beden", "تكلفة", "مقاس"]):
                c_name, q_str = l.split(":", 1)
                c_name = c_name.strip().lower()
                nums = [int(n) for n in q_str.replace(",", " ").split() if n.isdigit()]
                for i, q in enumerate(nums):
                    sz = sizes[i] if i < len(sizes) else f"T{i+1}"
                    new_id = (max([v["id"] for v in DATA_STORE["variants"]], default=0)) + 1
                    DATA_STORE["variants"].append({
                        "id": new_id,
                        "product_name": m_name,
                        "color": c_name,
                        "size": sz,
                        "quantity": q,
                        "cost_price": cost
                    })

        save_data()
        paste_panel.visible = False
        show_alert("✅ تم إضافة المنتجات للمخزن!")
        render_stock()

    paste_panel = ft.Container(
        visible=False,
        padding=10,
        bgcolor="#EEF2FF",
        border_radius=10,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text("📋 اللصق السريع", size=14, weight=ft.FontWeight.BOLD, color="#3730A3"),
                    ft.IconButton(ft.icons.CLOSE, icon_color="#4338CA", on_click=lambda e: setattr(paste_panel, 'visible', False) or page.update())
                ]),
                paste_field,
                ft.ElevatedButton("⚡ حفظ في المخزن", bgcolor="#4F46E5", color=ft.colors.WHITE, on_click=process_paste)
            ]
        )
    )

    # --- نافذة البيع ---
    sale_ctx = {}
    sale_q_in = ft.TextField(label="الكمية", value="1", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    sale_p_in = ft.TextField(label="سعر البيع", value="250", keyboard_type=ft.KeyboardType.NUMBER, dense=True)
    sale_ch = ft.Dropdown(label="القناة", value="Mağaza", options=[ft.dropdown.Option("Mağaza"), ft.dropdown.Option("Trendyol")])

    def show_sale_modal(v_id, name, color, size, qty, cost):
        sale_ctx.update({"id": v_id, "name": name, "color": color, "size": size, "max_qty": qty, "cost": cost})
        sale_panel.visible = True
        page.update()

    def do_sale(e):
        try:
            q = int(sale_q_in.value)
            p = float(sale_p_in.value)
        except Exception:
            show_alert("أرقام غير صالحة", is_error=True)
            return

        if q <= 0 or q > sale_ctx.get("max_qty", 0):
            show_alert("الكمية غير متاحة", is_error=True)
            return

        for v in DATA_STORE["variants"]:
            if v["id"] == sale_ctx["id"]:
                v["quantity"] -= q
                break

        ded = (p * q * 0.167) if sale_ch.value == "Trendyol" else 0.0
        DATA_STORE["sales"].append({
            "product_name": sale_ctx["name"],
            "color": sale_ctx["color"],
            "size": sale_ctx["size"],
            "quantity": q,
            "cost_price": sale_ctx["cost"],
            "sale_price": p,
            "channel": sale_ch.value,
            "deductions": ded,
            "sale_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        save_data()
        sale_panel.visible = False
        show_alert(f"✅ تم بيع {q} قطعة!")
        render_stock()

    sale_panel = ft.Container(
        visible=False,
        padding=10,
        bgcolor="#DCFCE7",
        border_radius=10,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text("🛍️ تسجيل بيع", size=13, weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.icons.CLOSE, on_click=lambda e: setattr(sale_panel, 'visible', False) or page.update())
                ]),
                sale_q_in,
                sale_p_in,
                sale_ch,
                ft.ElevatedButton("تأكيد وخصم", bgcolor="#16A34A", color=ft.colors.WHITE, on_click=do_sale)
            ]
        )
    )

    page.appbar = ft.AppBar(
        title=ft.Text("M&E Tekstil ERP", weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
        center_title=True,
        bgcolor="#0F172A",
        actions=[ft.IconButton(ft.icons.REFRESH, icon_color=ft.colors.WHITE, on_click=lambda e: render_stock())]
    )

    def kpi_box(title, val_w, icon_name, bg):
        return ft.Container(
            expand=True,
            padding=8,
            border_radius=8,
            bgcolor=bg,
            content=ft.Column(spacing=2, controls=[ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(title, size=10, color="#475569"), ft.Icon(icon_name, size=14, color="#475569")]), val_w])
        )

    dash_row = ft.Row(spacing=6, controls=[
        kpi_box("المخزن", stat_total_stock, ft.icons.INVENTORY_2, "#EFF6FF"),
        kpi_box("المبيعات", stat_today_sales, ft.icons.SHOPPING_BAG, "#EEF2FF"),
        kpi_box("الأرباح", stat_today_profit, ft.icons.ATTACH_MONEY, "#F0FDF4"),
    ])

    btn_row = ft.Row(spacing=4, controls=[
        ft.ElevatedButton("📋 لصق", bgcolor="#4F46E5", color=ft.colors.WHITE, on_click=lambda e: setattr(paste_panel, 'visible', not paste_panel.visible) or page.update()),
        ft.ElevatedButton("🧮 حاسبة", bgcolor="#D97706", color=ft.colors.WHITE, on_click=lambda e: setattr(calc_panel, 'visible', not calc_panel.visible) or page.update()),
        ft.ElevatedButton("📥 تصدير", bgcolor="#059669", color=ft.colors.WHITE, on_click=export_csv),
        ft.ElevatedButton("☁️ مزامنة", bgcolor="#0284C7", color=ft.colors.WHITE, on_click=sync_sheets),
    ])

    search_f = ft.TextField(
        hint_text="ابحث عن صنف أو لون...",
        prefix_icon=ft.icons.SEARCH,
        dense=True,
        on_change=lambda e: render_stock([it for it in DATA_STORE["variants"] if e.control.value.lower() in it["product_name"].lower() or e.control.value.lower() in it["color"].lower()])
    )

    page.add(
        status_banner,
        dash_row,
        ft.Container(height=2),
        btn_row,
        paste_panel,
        calc_panel,
        sale_panel,
        ft.Container(height=2),
        search_f,
        ft.Container(height=2),
        ft.Text("📦 قائمة المخزون", size=14, weight=ft.FontWeight.BOLD, color="#0F172A"),
        stock_list_view
    )

    render_stock()

# تشغيل التطبيق في وضع Embedded Mobile الصريح
if __name__ == "__main__":
    ft.app(main)
