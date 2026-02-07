import pymysql.cursors
import streamlit as st
import pandas as pd

if "cart" not in st.session_state:
    st.session_state.cart = {}
if "search_params" not in st.session_state:
    st.session_state.search_params = {}
if "last_results" not in st.session_state:
    st.session_state.last_results = []
if "open_expanders" not in st.session_state:
    st.session_state.open_expanders = set()

connection = pymysql.connect(
    host="localhost",
    user="api",
    password="finalproject",
    database="final_project",
    cursorclass=pymysql.cursors.DictCursor,
)
with connection:

    def searchInventory(
        name=None, category=None, rarity=None, maxprice=None, minprice=None
    ):
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute(
                "CALL SearchItems(%s, %s, %s, %s, %s);",
                (name, category, rarity, maxprice, minprice),
            )
            return cursor.fetchall()

    def getItem(id):
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Items WHERE item_id = %s;", id)
            return cursor.fetchall()

    def order(adventurer_id, items):
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT MAX(order_id) FROM Orders;")
            result = cursor.fetchone()
            newid = result["MAX(order_id)"] + 1

            cursor.execute(
                "INSERT INTO Orders VALUES(%s, %s, 0, NOW());",
                (newid + 1, adventurer_id),
            )
            connection.commit()
            for item_id, qty in items:
                cursor.execute(
                    "INSERT INTO OrderItems VALUES(%s, %s, %s);", (newid, item_id, qty)
                )
                connection.commit()
                cursor.execute(
                    "UPDATE Items SET stocked = stocked - %s WHERE item_id = %s;",
                    (qty, item_id),
                )
                connection.commit()
            cursor.execute("CALL SetOrderTotal(%s);", (newid,))
            connection.commit()

    def getOrder(id):
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT o.order_id,
                    o.adventurer_id,
                    o.purchase_time,
                    o.total_price AS total_order_value,
                    i.item_id,
                    i.name AS item_name,
                    i.category,
                    i.rarity,
                    i.price AS item_price,
                    oi.quantity,
                    (oi.quantity * i.price) AS line_value,
                    s.name AS shop_name
                FROM Orders o
                JOIN OrderItems oi ON o.order_id = oi.order_id
                JOIN Items i ON oi.item_id = i.item_id
                JOIN Shops s ON i.shop_id = s.shop_id
                WHERE o.order_id = %s
                ORDER BY line_value DESC, i.rarity;
            """,
                id,
            )
            for item in cursor.fetchall():
                print(item)

    def topSellers(days=0):
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute("CALL TopSellingItems(%s);", days)
            return cursor.fetchall()

    def refreshSummary():
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute("CALL RefreshSummary();")
            connection.commit()
            cursor.execute(
                "SELECT * FROM 90DaySalesSummary ORDER BY total_sold DESC, total_revenue DESC;"
            )
            return cursor.fetchall()

    def loggedIn(id):
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO Logins(adventurer_id, login_time) VALUES (%s, NOW());", id
            )
            connection.commit()

    def getAdventurers():
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT adventurer_id, name FROM Adventurers;")
            return cursor.fetchall()

    def updateTotals():
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute("CALL SetAllOrderTotals;")
            connection.commit()

    adv_rows = getAdventurers()
    USERS = [(row["adventurer_id"], row["name"]) for row in adv_rows]

    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if st.session_state.user is None:
        connection.ping(reconnect=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Adventurers;")
            result = cursor.fetchall()
        users = []
        for user in result:
            users.append(user["name"])
        st.markdown("Login Required")
        selected = st.selectbox("Select Adventurer:", ["Choose a user..."] + users)
        if st.button("Login"):
            selected_id = next(uid for uid, name in USERS if name == selected)
            st.session_state.user = selected
            st.session_state.user_id = selected_id
            loggedIn(selected_id)
            st.rerun()
        st.stop()

    with st.popover("Admin Panel", width="stretch"):
        with st.expander("Stock warnings"):
            connection.ping(reconnect=True)
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM Items;")
                inv = cursor.fetchall()
            for item in inv:
                if item["stocked"] == 0:
                    st.markdown(
                        f"*{item['name']}* **OUT OF STOCK** - {item['stocked']} in stock"
                    )
                elif (
                    (item["rarity"] == "Legendary" and item["stocked"] < 2)
                    or (item["rarity"] == "Very Rare" and item["stocked"] < 5)
                    or (item["rarity"] == "Rare" and item["stocked"] < 10)
                    or (item["rarity"] == "Uncommon" and item["stocked"] < 15)
                    or (item["rarity"] == "Common" and item["stocked"] < 20)
                    or (item["rarity"] == "Mundane" and item["stocked"] < 25)
                ):
                    st.markdown(
                        f"*{item['name']}* **LOW** - {item['stocked']} in stock"
                    )
        if "sales_table" not in st.session_state:
            st.session_state.sales_table = []
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("90-Day Sales Summary", key="btn_90day_summary"):
                st.session_state.sales_table = refreshSummary()
        with col2:
            if st.button("Yearly Sales Summary", key="btn_year_sellers"):
                st.session_state.sales_table = topSellers(365)
        with col3:
            if st.button("All-Time Sales Summary", key="btn_alltime_sellers"):
                st.session_state.sales_table = topSellers(0)
        with col4:
            if st.button("Update Order Totals", key="update_totals"):
                updateTotals()
        data = st.session_state.get("sales_table", [])
        df = pd.DataFrame(data)
        if not df.empty:
            total_items_sold = (
                df["total_sold"].sum() if "total_sold" in df.columns else 0
            )
            total_revenue = (
                df["total_revenue"].sum() if "total_revenue" in df.columns else 0
            )
            coll1, coll2 = st.columns(2)
            with coll1:
                st.write(f"Items sold: {total_items_sold}")
            with coll2:
                st.write(f"Total revenue: {total_revenue}")

            st.dataframe(df, hide_index=True)
        else:
            st.write("No sales data to display.")

    st.markdown(
        f"""
    <div style="background-color:#44444f; padding:10px; border-radius:5px;">
        <h1 style="color:#9261e8; text-align:center;">The Gnome Depot</h1>
        <h2 style="text-align:center;color:#d6cce8;">Magic Items & More!</h2>
        <p style="text-align:center;color:#ffffff;">Welcome {st.session_state.user}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.session_state.search_params.setdefault("query", "")
    query = st.text_input(
        "Search Inventory:",
        placeholder="I'm looking for...",
        value=st.session_state.search_params.get("query", ""),
    )

    with st.expander("Advanced Options"):
        prev = st.session_state.search_params
        category = st.selectbox(
            "Category:",
            [
                "Any",
                "Adventuring Gear",
                "Armor",
                "Tools",
                "Wondrous Items",
                "Weapons",
                "Poisons",
                "Potions & Oils",
                "Miscellaneous",
            ],
            index=0 if prev.get("category") is None else 0,
        )

        rarity = st.selectbox(
            "Rarity:",
            ["Any", "Mundane", "Common", "Uncommon", "Rare", "Very Rare", "Legendary"],
            index=0 if prev.get("rarity") is None else 0,
        )

        price = st.slider(
            "Price Range:",
            0,
            16500000,
            (prev.get("minprice", 0), prev.get("maxprice", 16500000)),
        )

    search_btn = st.button("Go")
    if search_btn:
        search_category = None if category == "Any" else category
        search_rarity = None if rarity == "Any" else rarity

        st.session_state.search_params = {
            "query": query,
            "category": search_category,
            "rarity": search_rarity,
            "minprice": price[0],
            "maxprice": price[1],
        }

        st.session_state.last_results = searchInventory(
            query, search_category, search_rarity, price[0], price[1]
        )
        results = st.session_state.last_results
    else:
        results = st.session_state.last_results

    for item in results:
        item_id = str(item["item_id"])
        expanded = item["item_id"] in st.session_state.open_expanders
        if item["description"] == "nan":
            item["description"] = "No description given."
        with st.expander(item["name"], expanded=expanded):
            st.markdown(f"***{item['rarity']} / {item['category']}***")
            st.markdown(f"**Price**: {item['price']}g")
            st.write(item["description"])
            st.markdown(f"**{item['stocked']}** in stock")
            sold_by = None
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT name FROM Shops WHERE shop_id = %s;", item["shop_id"]
                )
                shop = cursor.fetchall()
                if shop:
                    sold_by = shop[0]["name"]
            if sold_by:
                st.markdown(f"Sold by *{sold_by}*")
            if item["stocked"] == 0:
                st.markdown("**OUT OF STOCK**")
            elif (
                (item["rarity"] == "Legendary" and item["stocked"] < 2)
                or (item["rarity"] == "Very Rare" and item["stocked"] < 5)
                or (item["rarity"] == "Rare" and item["stocked"] < 10)
                or (item["rarity"] == "Uncommon" and item["stocked"] < 15)
                or (item["rarity"] == "Common" and item["stocked"] < 20)
                or (item["rarity"] == "Mundane" and item["stocked"] < 25)
            ):
                st.markdown(f"Low stock!")
            current_qty = st.session_state.cart.get(item_id, 0)
            with st.form(key=f"form_{item_id}"):
                qty = st.number_input(
                    "Quantity:",
                    0,
                    item["stocked"],
                    value=current_qty,
                    key=f"qty_{item_id}",
                )
                submit = st.form_submit_button("Update Cart")

                if submit:
                    if qty > 0:
                        st.session_state.cart[item_id] = qty
                    else:
                        st.session_state.cart.pop(item_id, None)
                    st.session_state.open_expanders.add(item["item_id"])
                    prev = st.session_state.search_params
                    st.session_state.last_results = searchInventory(
                        prev.get("query") or None,
                        prev.get("category"),
                        prev.get("rarity"),
                        prev.get("maxprice"),
                        prev.get("minprice"),
                    )
                    st.rerun()

    st.sidebar.write("**Cart:**")
    if st.session_state.cart:
        sidebar_cart_total = 0
        for item_id, quantity in list(st.session_state.cart.items()):
            row = getItem(item_id)[0]
            line_cost = row["price"] * quantity
            sidebar_cart_total += line_cost

            col1, col2 = st.sidebar.columns([6, 1])
            with col1:
                st.write(f"{quantity} {row['name']}  ({line_cost}g)")
            with col2:
                if st.button("X", key=f"trash_{item_id}"):
                    del st.session_state.cart[item_id]
                    prev = st.session_state.get("search_params", {})
                    st.session_state.last_results = searchInventory(
                        prev.get("query"),
                        prev.get("category"),
                        prev.get("rarity"),
                        prev.get("minprice"),
                        prev.get("maxprice"),
                    )
                    st.rerun()

    st.sidebar.write("---")
    st.sidebar.write(
        f"**Total: {sum(getItem(i)[0]['price'] * q for i, q in st.session_state.cart.items())}g**"
    )

    @st.dialog("Order Summary")
    def confirm_order_dialog():
        st.write("Items in Order:")
        items_for_order = []
        for item_id, qty in st.session_state.cart.items():
            row = getItem(item_id)[0]
            st.write(f"**{qty} {row['name']}** {row['price']}g each")
            items_for_order.append((item_id, qty))
        if not items_for_order:
            st.write("Cart is empty!")
            if st.button("Close", key="close_empty_dialog"):
                return
        else:
            if st.button("Continue", key="continue_checkout"):
                order(st.session_state.user_id, items_for_order)
                st.session_state.cart = {}
                st.session_state.open_expanders = set()

                st.rerun()

    if st.sidebar.button("Checkout", key="launch_checkout_dialog"):
        confirm_order_dialog()
