import flet as ft
from database import init_db, get_all_stock, record_sale, add_or_update_variant, get_financial_summary
from ai_engine import analyze_intent

def main(page: ft.Page):
    page.title = "M&E Tekstil ERP"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO
    
    init_db()

    # --- عناصر التنبيهات السريعة ---
    def show_snackbar(text, color=ft.Colors.GREEN):
        snack = ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=color)
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # --- 1. قسم الإحصائيات العلوية ---
    def build_dashboard():
        stats = get_financial_summary(days=1)
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("📊 تقرير مبيعات اليوم", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([
                        ft.Column([ft.Text("القطع المباعة"), ft.Text(f"{stats['total_sold']} قطعة", weight=ft.FontWeight.BOLD, size=16)]),
                        ft.Column([ft.Text("إجمالي الإيراد"), ft.Text(f"{stats['total_revenue']:.2f} TL", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.BLUE)]),
                        ft.Column([ft.Text("صافي الربح"), ft.Text(f"+{stats['net_profit']:.2f} TL", weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.GREEN)]),
                    ], alignment=ft.MainAxisAlignment.SPACE_AROUND)
                ]),
                padding=16
            )
        )

    # --- 2. قسم المساعد الذكي ---
    ai_input = ft.TextField(
        hint_text="اكتب بالعامية (مثال: سجل بيع 1 بنطلون اسود 34 ترينديول بـ 450)",
        expand=True,
        border_radius=12
    )

    def process_ai_command(e):
        if not ai_input.value.strip():
            return
        
        show_snackbar("🤖 جاري معالجة الطلب بالذكاء الاصطناعي...", color=ft.Colors.BLUE_GREY)
        res = analyze_intent(ai_input.value)
        intent = res.get("intent")

        if intent == "record_sale":
            ok, msg = record_sale(
                prod=res.get("product_name", "pantolon"),
                color=res.get("color", "siyah"),
                size=res.get("size", "M"),
                qty=int(res.get("quantity", 1)),
                sale_price=float(res.get("sale_price", 250)),
                channel=res.get("channel", "Mağaza"),
                shipping_cost=float(res.get("shipping_cost", 0.0))
            )
            if ok:
                show_snackbar(f"✅ تم تسجيل البيع! صافي الربح: +{msg['net_profit']:.2f} TL")
                ai_input.value = ""
                refresh_view()
            else:
                show_snackbar(f"⚠️ {msg}", color=ft.Colors.RED)

        elif intent == "add_stock":
            prod = res.get("product_name", "atlet")
            color = res.get("color", "siyah")
            items = res.get("items", [])
            for it in items:
                add_or_update_variant(
                    prod=prod,
                    color=color,
                    size=it.get("size", "M"),
                    qty=int(it.get("quantity", 10)),
                    cost=float(it.get("cost_price", 95.0))
                )
            show_snackbar("✅ تم إضافة المنتجات إلى المخزون بنجاح!")
            ai_input.value = ""
            refresh_view()

    ai_section = ft.Container(
        content=ft.Column([
            ft.Text("⚡ المساعد والمدخل الذكي (AI)", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([
                ai_input,
                ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color=ft.Colors.BLUE, on_click=process_ai_command)
            ])
        ]),
        padding=10
    )

    # --- 3. قسم عرض المخزون ---
    stock_list_view = ft.ListView(expand=1, spacing=10, height=350)

    def refresh_stock_list():
        stock_list_view.controls.clear()
        stock = get_all_stock()
        if not stock:
            stock_list_view.controls.append(ft.Text("لا يوجد منتجات مسجلة في المخزون حتى الآن.", text_align=ft.TextAlign.CENTER))
            return

        for item in stock:
            qty = item["quantity"]
            status_color = ft.Colors.GREEN if qty > 3 else (ft.Colors.ORANGE if qty > 0 else ft.Colors.RED)
            
            stock_list_view.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECKROOM, color=ft.Colors.BLUE_GREY),
                        ft.Column([
                            ft.Text(f"{item['product_name'].title()} - {item['color'].title()}", weight=ft.FontWeight.BOLD),
                            ft.Text(f"المقاس: {item['size']} | التكلفة: {item['cost_price']} TL", size=12, color=ft.Colors.GREY_700),
                        ], expand=True),
                        ft.Container(
                            content=ft.Text(f"{qty} قطعة", color=ft.Colors.WHITE, size=12, weight=ft.FontWeight.BOLD),
                            bgcolor=status_color,
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            border_radius=8
                        )
                    ]),
                    padding=10,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10
                )
            )

    def refresh_view():
        main_layout.controls[0] = build_dashboard()
        refresh_stock_list()
        page.update()

    refresh_stock_list()

    main_layout = ft.Column([
        build_dashboard(),
        ai_section,
        ft.Text("📦 حالة المخزون الحالي", size=16, weight=ft.FontWeight.BOLD),
        stock_list_view
    ], expand=True)

    page.add(main_layout)

if __name__ == "__main__":
    ft.app(target=main)
