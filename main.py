import flet as ft
from database import init_db, get_all_stock, record_sale, add_or_update_variant, get_financial_summary
from ai_engine import analyze_intent

def main(page: ft.Page):
    page.title = "M&E Tekstil ERP"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    
    init_db()

    def show_snackbar(text, color=ft.Colors.GREEN):
        snack = ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=color)
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # ----------------------------------------------------
    # 1. نافذة البيع السريع (Quick Sale Dialog)
    # ----------------------------------------------------
    sale_prod = ft.Ref[str]()
    sale_color = ft.Ref[str]()
    sale_size = ft.Ref[str]()
    sale_cost = ft.Ref[float]()

    price_field = ft.TextField(label="سعر البيع (TL)", keyboard_type=ft.KeyboardType.NUMBER)
    channel_dropdown = ft.Dropdown(
        label="قناة البيع (Kanal)",
        options=[
            ft.dropdown.Option("Mağaza", "🏬 Mağaza (متجر / يدوي)"),
            ft.dropdown.Option("Trendyol", "🌐 Trendyol (%16.7 عمولة)")
        ],
        value="Mağaza"
    )
    shipping_field = ft.TextField(label="تكلفة الشحن (Trendyol Kargo TL)", value="0", keyboard_type=ft.KeyboardType.NUMBER, visible=False)

    def on_channel_change(e):
        shipping_field.visible = (channel_dropdown.value == "Trendyol")
        if shipping_field.visible and (not shipping_field.value or shipping_field.value == "0"):
            shipping_field.value = "30"
        page.update()

    channel_dropdown.on_change = on_channel_change

    def close_dialog(e):
        sale_dialog.open = False
        page.update()

    def confirm_quick_sale(e):
        try:
            val_str = str(price_field.value or "").replace(",", ".").strip()
            p = float(val_str)
            ship_str = str(shipping_field.value or "0").replace(",", ".").strip()
            ship = float(ship_str) if shipping_field.visible else 0.0
        except Exception:
            show_snackbar("⚠️ يرجى إدخال سعر صحيح", color=ft.Colors.RED)
            return

        ok, msg = record_sale(
            prod=sale_prod.current,
            color=sale_color.current,
            size=sale_size.current,
            qty=1,
            sale_price=p,
            channel=channel_dropdown.value,
            shipping_cost=ship
        )
        sale_dialog.open = False
        if ok:
            show_snackbar(f"✅ تم البيع! الربح: +{msg['net_profit']:.2f} TL")
            refresh_all()
        else:
            show_snackbar(f"⚠️ {msg}", color=ft.Colors.RED)
        page.update()

    sale_dialog = ft.AlertDialog(
        title=ft.Text("تسجيل عملية بيع"),
        content=ft.Column([
            price_field,
            channel_dropdown,
            shipping_field
        ], tight=True, spacing=12),
        actions=[
            ft.TextButton("إلغاء", on_click=close_dialog),
            ft.ElevatedButton("تأكيد البيع", bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE, on_click=confirm_quick_sale)
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )
    page.overlay.append(sale_dialog)

    def open_sale_modal(prod, color, size, cost):
        sale_prod.current = str(prod)
        sale_color.current = str(color)
        sale_size.current = str(size)
        sale_cost.current = float(cost)
        price_field.value = ""
        channel_dropdown.value = "Mağaza"
        shipping_field.visible = False
        sale_dialog.title = ft.Text(f"بيع: {str(prod).title()} - {str(color).title()} ({size})")
        sale_dialog.open = True
        page.update()

    # ----------------------------------------------------
    # 2. التبويب الأول: المخزون المجمّع والمنسدل
    # ----------------------------------------------------
    search_query = ft.TextField(hint_text="بحث عن موديل أو لون...", expand=True, prefix_icon=ft.Icons.SEARCH)
    filter_low_stock = ft.Switch(label="أوشك على النفاد ⚠️", value=False)
    stock_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def quick_add_one(prod, color, size, cost):
        add_or_update_variant(prod=str(prod), color=str(color), size=str(size), qty=1, cost=float(cost))
        show_snackbar(f"✅ تم إضافة +1 إلى {str(prod).title()} ({size})")
        refresh_all()

    def build_stock_view():
        stock_container.controls.clear()
        raw_stock = get_all_stock()
        
        grouped = {}
        for r in raw_stock:
            p_name = str(r.get("product_name") or "")
            c_name = str(r.get("color") or "")
            key = (p_name, c_name)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(r)

        q = (search_query.value or "").strip().lower()
        only_low = bool(filter_low_stock.value)

        for (prod, color), variants in grouped.items():
            if q and (q not in prod.lower() and q not in color.lower()):
                continue

            total_qty = sum(int(v.get("quantity") or 0) for v in variants)
            if only_low and not any(int(v.get("quantity") or 0) <= 3 for v in variants):
                continue

            sizes_column = ft.Column(spacing=8, visible=False)
            arrow_icon = ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN)

            for v in variants:
                s_qty = int(v.get("quantity") or 0)
                cost_val = float(v.get("cost_price") or 0.0)
                s_name = str(v.get("size") or "-")
                badge_col = ft.Colors.GREEN if s_qty > 3 else (ft.Colors.ORANGE if s_qty > 0 else ft.Colors.RED)
                
                sizes_column.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"مقاس: {s_name}", weight=ft.FontWeight.BOLD, expand=True),
                            ft.Text(f"التكلفة: {cost_val:.2f} TL", size=12, color=ft.Colors.GREY_700),
                            ft.Container(
                                content=ft.Text(f"{s_qty} قطعة", color=ft.Colors.WHITE, size=11, weight=ft.FontWeight.BOLD),
                                bgcolor=badge_col,
                                padding=6,
                                border_radius=6
                            ),
                            ft.IconButton(
                                icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                icon_color=ft.Colors.RED_600,
                                tooltip="تسجيل بيع (-1)",
                                on_click=lambda e, p=prod, c=color, s=s_name, cost=cost_val: open_sale_modal(p, c, s, cost)
                            ),
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                icon_color=ft.Colors.GREEN_600,
                                tooltip="إضافة قطعة (+1)",
                                on_click=lambda e, p=prod, c=color, s=s_name, cost=cost_val: quick_add_one(p, c, s, cost)
                            )
                        ]),
                        bgcolor=ft.Colors.GREY_50,
                        padding=8,
                        border_radius=8
                    )
                )

            def make_toggle(col, icon):
                def toggle(e):
                    col.visible = not col.visible
                    icon.name = ft.Icons.KEYBOARD_ARROW_UP if col.visible else ft.Icons.KEYBOARD_ARROW_DOWN
                    page.update()
                return toggle

            stock_container.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Container(
                                on_click=make_toggle(sizes_column, arrow_icon),
                                content=ft.Row([
                                    ft.Icon(ft.Icons.CHECKROOM, color=ft.Colors.BLUE_900),
                                    ft.Column([
                                        ft.Text(f"{prod.title()} - {color.title()}", weight=ft.FontWeight.BOLD, size=15),
                                        ft.Text(f"إجمالي المخزون: {total_qty} قطعة (اضغط للتفاصيل)", size=12, color=ft.Colors.BLUE_GREY),
                                    ], expand=True),
                                    arrow_icon
                                ]),
                                padding=4
                            ),
                            sizes_column
                        ]),
                        padding=10
                    )
                )
            )
        page.update()

    search_query.on_change = lambda e: build_stock_view()
    filter_low_stock.on_change = lambda e: build_stock_view()

    tab_stock = ft.Column([
        ft.Row([search_query]),
        ft.Row([filter_low_stock], alignment=ft.MainAxisAlignment.END),
        stock_container
    ], expand=True)

    # ----------------------------------------------------
    # 3. التبويب الثاني: المساعد الذكي ولوحة المبيعات
    # ----------------------------------------------------
    dashboard_card = ft.Container()

    def update_dashboard():
        stats = get_financial_summary(days=1)
        sold_count = int(stats.get("total_sold") or 0)
        rev = float(stats.get("total_revenue") or 0.0)
        prof = float(stats.get("net_profit") or 0.0)

        dashboard_card.content = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("📊 تقرير مبيعات اليوم (Günlük Rapor)", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([
                        ft.Column([ft.Text("المباع"), ft.Text(f"{sold_count} قطعة", weight=ft.FontWeight.BOLD, size=15)]),
                        ft.Column([ft.Text("الإيراد"), ft.Text(f"{rev:.2f} TL", weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.BLUE)]),
                        ft.Column([ft.Text("الربح"), ft.Text(f"+{prof:.2f} TL", weight=ft.FontWeight.BOLD, size=15, color=ft.Colors.GREEN)]),
                    ], alignment=ft.MainAxisAlignment.SPACE_AROUND)
                ]),
                padding=14
            )
        )

    ai_input = ft.TextField(
        hint_text="اكتب بالعامية (مثال: سجل بيع 1 بنطلون اسود 34 ترينديول بـ 450)",
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=3,
        border_radius=12
    )

    def process_ai_command(e):
        if not ai_input.value or not ai_input.value.strip():
            return
        show_snackbar("🤖 جاري المعالجة بالذكاء الاصطناعي...", color=ft.Colors.BLUE_GREY)
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
                show_snackbar(f"✅ تم تسجيل البيع! الربح: +{msg['net_profit']:.2f} TL")
                ai_input.value = ""
                refresh_all()
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
            refresh_all()

    tab_ai = ft.Column([
        dashboard_card,
        ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("⚡ المساعد والمدخل الذكي (AI Assistant)", weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ai_input,
                        ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color=ft.Colors.BLUE, on_click=process_ai_command)
                    ])
                ]),
                padding=12
            )
        )
    ], scroll=ft.ScrollMode.AUTO, expand=True)

    # ----------------------------------------------------
    # 4. التبويب الثالث: الأدوات والملصقات
    # ----------------------------------------------------
    tab_tools = ft.Column([
        ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🏷️ إدارة الباركود والملصقات (70x42 mm)", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text("توليد ملفات PDF قياسية جاهزة للطباعة على ورق 21 ملصق.", size=12, color=ft.Colors.GREY_700),
                    ft.ElevatedButton("طباعة ملصقات المخزون الحالي", icon=ft.Icons.PRINT, bgcolor=ft.Colors.BLUE_GREY, color=ft.Colors.WHITE)
                ]),
                padding=16
            )
        )
    ], expand=True)

    # ----------------------------------------------------
    # 5. شريط التنقل السفلي والتبديل بين الشاشات
    # ----------------------------------------------------
    current_tab = ft.Column([tab_stock], expand=True)

    def on_nav_change(e):
        idx = int(e.control.selected_index)
        current_tab.controls.clear()
        if idx == 0:
            current_tab.controls.append(tab_stock)
            build_stock_view()
        elif idx == 1:
            current_tab.controls.append(tab_ai)
            update_dashboard()
        elif idx == 2:
            current_tab.controls.append(tab_tools)
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.INVENTORY_2_OUTLINED, selected_icon=ft.Icons.INVENTORY_2, label="المخزون"),
            ft.NavigationBarDestination(icon=ft.Icons.AUTO_AWESOME_OUTLINED, selected_icon=ft.Icons.AUTO_AWESOME, label="المساعد & البيع"),
            ft.NavigationBarDestination(icon=ft.Icons.PRINT_OUTLINED, selected_icon=ft.Icons.PRINT, label="الملصقات"),
        ]
    )

    def refresh_all():
        update_dashboard()
        build_stock_view()

    page.add(current_tab)
    refresh_all()

if __name__ == "__main__":
    ft.app(target=main)
