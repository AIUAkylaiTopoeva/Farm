import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

API_BASE = "http://127.0.0.1:8000/api"

st.set_page_config(
    page_title="AgroMap",
    layout="wide"
)

# --------------------------
# SESSION
# --------------------------

if "token" not in st.session_state:
    st.session_state.token = None

if "selected_products" not in st.session_state:
    st.session_state.selected_products = set()

# --------------------------
# STYLE
# --------------------------

def inject_css():

    st.markdown("""
<style>

body {
background:#f5f7f6;
font-family: Inter;
}

/* NAVBAR */

.navbar{
display:flex;
justify-content:space-between;
align-items:center;
padding:20px;
background:white;
border-radius:12px;
box-shadow:0 8px 20px rgba(0,0,0,0.05);
margin-bottom:30px;
}

.logo{
font-weight:700;
font-size:22px;
color:#2e7d32;
}

/* HERO */

.hero{
background:white;
padding:30px;
border-radius:16px;
box-shadow:0 10px 25px rgba(0,0,0,0.05);
margin-bottom:30px;
}

.hero-title{
font-size:28px;
font-weight:700;
margin-bottom:10px;
color:#1b5e20;
}

.hero-sub{
font-size:15px;
color:#6c7a70;
}

/* PRODUCT CARD */

.product-card{
background:white;
padding:18px;
border-radius:14px;
box-shadow:0 6px 20px rgba(0,0,0,0.05);
transition:0.2s;
}

.product-card:hover{
transform:translateY(-3px);
}

.product-title{
font-weight:600;
font-size:16px;
margin-bottom:6px;
}

.product-price{
font-weight:700;
color:#2e7d32;
margin-top:6px;
}

/* FILTER BOX */

.filter-box{
background:white;
padding:20px;
border-radius:12px;
box-shadow:0 6px 20px rgba(0,0,0,0.05);
margin-bottom:25px;
}

div.stButton > button{
background:#2e7d32;
color:white;
border-radius:8px;
border:none;
padding:10px 18px;
font-weight:600;
}

div.stButton > button:hover{
background:#1b5e20;
}

</style>
""", unsafe_allow_html=True)

inject_css()

# --------------------------
# API HELPERS
# --------------------------

def api_post(path, json=None, headers=None):

    try:
        return requests.post(
            f"{API_BASE}{path}",
            json=json,
            headers=headers,
            timeout=10
        )

    except:
        st.error("API недоступен. Запусти Django сервер.")
        return None


def api_get(path, params=None, headers=None):

    try:
        return requests.get(
            f"{API_BASE}{path}",
            params=params,
            headers=headers,
            timeout=10
        )

    except:
        st.error("API недоступен. Запусти Django сервер.")
        return None

# --------------------------
# LOGIN
# --------------------------

def login():

    st.markdown("""
<div class="navbar">
<div class="logo">AgroMap</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="hero">
<div class="hero-title">Вход в AgroMap</div>
<div class="hero-sub">
Платформа локальных фермерских продуктов и оптимизации маршрутов.
</div>
</div>
""", unsafe_allow_html=True)

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        r = api_post("/accounts/login/", {
            "email": email,
            "password": password
        })

        if r and r.status_code == 200:

            data = r.json()

            st.session_state.token = data["access"]

            st.success("Успешный вход")

            st.rerun()

        else:
            st.error("Ошибка входа")

# --------------------------
# PRODUCTS
# --------------------------

def get_products(params=None):

    r = api_get("/market/products/", params=params)

    if r and r.status_code == 200:
        return r.json()

    return []

# --------------------------
# ROUTE
# --------------------------

def optimize_route(product_ids):

    headers = {
        "Authorization": f"Bearer {st.session_state.token}"
    }

    payload = {
        "product_ids": product_ids
    }

    r = api_post(
        "/routing/optimize/",
        json=payload,
        headers=headers
    )

    if r and r.status_code == 200:

        return r.json()

    st.error("Не удалось построить маршрут")

    return None

# --------------------------
# MAP
# --------------------------

def show_map(route):

    points = route["points"]

    center = [points[0]["lat"], points[0]["lon"]]

    m = folium.Map(location=center, zoom_start=11)

    coords = []

    for p in points:

        coords.append([p["lat"], p["lon"]])

        folium.Marker(
            [p["lat"], p["lon"]],
            popup=p["farm_name"]
        ).add_to(m)

    folium.PolyLine(coords).add_to(m)

    st_folium(m, width=700)

# --------------------------
# CATALOG PAGE
# --------------------------

def catalog():

    st.markdown("""
<div class="navbar">
<div class="logo">AgroMap</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="hero">
<div class="hero-title">Каталог продуктов</div>
<div class="hero-sub">
Выбирайте продукты и стройте оптимальный маршрут по фермам.
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="filter-box">', unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)

    with c1:
        q = st.text_input("Поиск")

    with c2:
        min_price = st.number_input("Мин цена",0)

    with c3:
        max_price = st.number_input("Макс цена",10000)

    st.markdown('</div>', unsafe_allow_html=True)

    params = {}

    if q:
        params["q"] = q

    if min_price:
        params["min_price"] = min_price

    if max_price:
        params["max_price"] = max_price

    products = get_products(params)

    cols = st.columns(3)

    for i,p in enumerate(products):

        with cols[i % 3]:

            st.markdown(f"""
<div class="product-card">
<div class="product-title">{p['title']}</div>
<div>{p['description'][:80]}</div>
<div class="product-price">{p['price']} KGS</div>
</div>
""", unsafe_allow_html=True)

            pid = p["id"]

            if st.checkbox("Добавить в маршрут", key=pid):

                st.session_state.selected_products.add(pid)

    if st.button("Построить маршрут"):

        ids = list(st.session_state.selected_products)

        if len(ids) < 2:
            st.warning("Выберите минимум 2 продукта")
            return

        route = optimize_route(ids)

        if route:

            left,right = st.columns([2,1])

            with left:
                show_map(route)

            with right:

                st.metric(
                    "Naive distance",
                    route["naive_distance_km"]
                )

                st.metric(
                    "Optimized distance",
                    route["optimized_distance_km"]
                )

# --------------------------
# PROFILE
# --------------------------

def profile():

    headers = {
        "Authorization": f"Bearer {st.session_state.token}"
    }

    r = api_get(
        "/accounts/me/",
        headers=headers
    )

    if r.status_code != 200:

        st.error("Ошибка загрузки профиля")

        return

    user = r.json()

    st.title("Профиль")

    st.write("Email:", user["email"])
    st.write("Role:", user["role"])

# --------------------------
# MAIN
# --------------------------

if not st.session_state.token:

    login()

else:

    page = st.sidebar.selectbox(
        "Навигация",
        ["Каталог","Профиль"]
    )

    if page == "Каталог":
        catalog()

    if page == "Профиль":
        profile()