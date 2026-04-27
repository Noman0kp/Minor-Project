"""
app.py  —  Sustainable Product Recommendation System
=====================================================
Main Streamlit application.

Tabs:
  🔍 Product Search     — search any keyword, compare eco variants side-by-side
  🎯 My Recommendations — personalised CF picks, weight-adjustable eco ranking
  ⭐ My Ratings         — view all your product ratings
  📈 Analytics          — platform-wide charts

Auth:
  Login / Register / Forgot Password  (SQLite via database.py)

Run:
  1. python seed_data.py      ← first time only
  2. streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from database import (
    create_tables,
    login_user,
    register_user,
    get_user_by_identifier,
    get_all_products,
    get_user_ratings,
    add_rating,
    get_stats,
)
from recommender import (
    load_ratings_df,
    load_products_df,
    get_base_recommendations,
    apply_weights,
    search_and_recommend,
)


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session():
    """Initialise all session_state keys exactly once per browser session."""
    defaults = {
        "logged_in":     False,
        "username":      "",
        "email":         "",
        "show_register": False,
        "show_forgot":   False,
        "recs_base":     None,   # cached CF candidates DataFrame
        "recs_user":     "",     # whose data is cached
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def do_login(username: str, email: str):
    st.session_state.update({
        "logged_in":     True,
        "username":      username,
        "email":         email,
        "show_register": False,
        "show_forgot":   False,
    })


def do_logout():
    st.session_state.update({
        "logged_in": False,
        "username":  "",
        "email":     "",
        "recs_base": None,
        "recs_user": "",
    })


# ============================================================================
# AUTH PAGES
# ============================================================================

def show_auth_page():
    _, centre, _ = st.columns([1, 2, 1])
    with centre:
        st.markdown("## 🌱 Sustainable Product Recommender")
        if st.session_state["show_register"]:
            _register_form()
        else:
            _login_form()


def _login_form():
    st.markdown("### 🔐 Login to Your Account")
    st.markdown("---")

    with st.form("login_form"):
        username  = st.text_input("Username", placeholder="Enter your username")
        password  = st.text_input("Password", type="password",
                                  placeholder="Enter your password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        if not username or not password:
            st.error("Please fill in both fields.")
        else:
            result = login_user(username, password)
            if result["success"]:
                do_login(username, result["email"])
                st.rerun()
            else:
                st.error(f"❌  {result['error']}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Create Account", use_container_width=True):
            st.session_state["show_register"] = True
            st.session_state["show_forgot"]   = False
            st.rerun()
    with col2:
        label = "🔼 Hide" if st.session_state["show_forgot"] else "🔑 Forgot Password?"
        if st.button(label, use_container_width=True):
            st.session_state["show_forgot"] = not st.session_state["show_forgot"]
            st.rerun()

    if st.session_state["show_forgot"]:
        _forgot_form()

    st.markdown("---")
    st.caption(
        "**Demo accounts** · username: `alice` … `olivia` or `admin` · "
        "password: `demo1234`"
    )


def _register_form():
    st.markdown("### 📝 Create a New Account")
    st.markdown("---")

    with st.form("reg_form"):
        uname = st.text_input("Username",         placeholder="min. 3 characters")
        email = st.text_input("Email",            placeholder="you@example.com")
        pw1   = st.text_input("Password",         type="password",
                              placeholder="min. 6 characters")
        pw2   = st.text_input("Confirm Password", type="password",
                              placeholder="repeat your password")
        ok    = st.form_submit_button("Create Account", use_container_width=True)

    if ok:
        if not all([uname, email, pw1, pw2]):
            st.error("Please fill in all fields.")
        elif pw1 != pw2:
            st.error("❌  Passwords do not match.")
        else:
            result = register_user(uname, pw1, email)
            if result["success"]:
                st.success("✅  Account created! You can now log in.")
                st.session_state["show_register"] = False
                st.rerun()
            else:
                st.error(f"❌  {result['error']}")

    st.markdown("---")
    if st.button("← Back to Login", use_container_width=True):
        st.session_state["show_register"] = False
        st.rerun()


def _forgot_form():
    st.markdown("#### 📧 Reset Your Password")
    st.info("Enter your username or email. A reset link will be simulated.")

    with st.form("forgot_form"):
        identifier = st.text_input("Username or Email")
        ok         = st.form_submit_button("Send Reset Link", use_container_width=True)

    if ok:
        if not identifier.strip():
            st.warning("Please enter your username or email.")
        else:
            user = get_user_by_identifier(identifier)
            if user:
                em = user["email"]
                local, domain = em.split("@")
                masked = local[:2] + "***@" + domain
                st.success(
                    f"✅  Password reset link sent to **{masked}**  "
                    f"*(simulation — no real email sent)*."
                )
            else:
                st.success(
                    "✅  If that account exists, a reset link has been sent "
                    "*(simulation)*."
                )


# ============================================================================
# MAIN APP
# ============================================================================

def show_main_app():
    st.title("🌱 Sustainable Product Recommender")
    st.markdown(
        "Find eco-friendly alternatives · Get personalised picks · Rate what you've tried."
    )

    ratings_df  = load_ratings_df()
    products_df = load_products_df()

    # ---- Sidebar -----------------------------------------------------------
    with st.sidebar:
        st.header("⚙️  Settings")
        st.markdown(f"👤 **{st.session_state['username']}**")
        st.caption(st.session_state["email"])

        if st.button("🚪 Logout", use_container_width=True):
            do_logout()
            st.rerun()

        st.divider()
        st.subheader("Algorithm Weights")
        st.caption(
            "Slide right → prioritise predicted rating.  \n"
            "Slide left  → prioritise eco score."
        )
        rating_w = st.slider("⭐ Rating Weight", 0.0, 1.0, 0.7, 0.1)
        eco_w    = round(1.0 - rating_w, 1)
        st.metric("🌿 Eco Weight", f"{eco_w:.1f}")
        if st.session_state["recs_base"] is not None:
            st.caption("⚡ Eco ranking updates live as you move the slider.")

        st.divider()
        stats = get_stats()
        st.subheader("📊 Database Stats")
        st.metric("Registered Users",      stats["total_users"])
        st.metric("Products in Catalogue", stats["total_products"])
        st.metric("Total Ratings",         stats["total_ratings"])
        st.metric("Platform Avg Rating",   f"⭐ {stats['avg_rating']}")

    # ---- Tabs --------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Product Search",
        "🎯 My Recommendations",
        "⭐ My Ratings",
        "📈 Analytics",
    ])

    # ====================================================================
    # TAB 1 — PRODUCT SEARCH + SUSTAINABILITY COMPARISON
    # ====================================================================
    with tab1:
        st.subheader("🔍 Search Products — Compare Eco Variants")
        st.markdown(
            "Type any product name to see **every sustainability variant** ranked "
            "greenest-first.  Rate products here to improve your recommendations."
        )

        query = st.text_input(
            "Search",
            placeholder="Try: laptop · t-shirt · coffee · backpack · yoga mat …",
            label_visibility="collapsed",
        )

        if query.strip():
            results = search_and_recommend(query)

            if results.empty:
                st.warning(
                    f"No products found for **'{query}'**.  "
                    "Try a shorter keyword like 'laptop', 'shirt', or 'coffee'."
                )
            else:
                st.success(
                    f"Found **{len(results)} variant(s)** for '**{query}**' — "
                    "ranked most eco-friendly first."
                )
                st.markdown(
                    "**Eco Score:**  "
                    "🔴 1 = Very Low  |  🟠 2 = Low  |  "
                    "🟡 3 = Moderate  |  🟢 4 = Good  |  ✅ 5 = Excellent"
                )
                st.markdown("---")

                for _, row in results.iterrows():
                    score = int(row["sustainability_score"])
                    badge = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "✅"}[score]
                    bar   = "█" * score + "░" * (5 - score)
                    price = (
                        f"₹ {row['price']:.2f}"
                        if pd.notna(row.get("price")) and row["price"]
                        else "—"
                    )

                    with st.container(border=True):
                        left, right = st.columns([4, 2])

                        with left:
                            st.markdown(f"### {row['product_name']}")
                            a, b, c = st.columns(3)
                            a.markdown(f"**Brand** · {row.get('brand','—')}")
                            b.markdown(f"**Category** · {row['category']}")
                            c.markdown(f"**Price** · {price}")
                            st.markdown(
                                f"**Eco Label:** `{row.get('eco_label','None')}`"
                            )
                            if row.get("description"):
                                st.caption(row["description"])

                        with right:
                            st.markdown(
                                f"<div style='text-align:center;padding:12px;"
                                f"border-radius:10px;background:rgba(39,174,96,0.1);'>"
                                f"<span style='font-size:2.2rem'>{badge}</span><br>"
                                f"<span style='font-size:1.6rem;font-weight:bold'>"
                                f"{score}/5</span><br>"
                                f"<code style='font-size:1rem'>{bar}</code><br>"
                                f"<small>Sustainability Score</small></div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown("")
                            user_rating = st.slider(
                                "Rate it",
                                1.0, 5.0, 3.0, 0.5,
                                key=f"sl_{row['product_id']}",
                            )
                            if st.button(
                                "⭐ Submit Rating",
                                key=f"rb_{row['product_id']}",
                                use_container_width=True,
                            ):
                                res = add_rating(
                                    st.session_state["username"],
                                    row["product_id"],
                                    user_rating,
                                )
                                if res["success"]:
                                    st.success("Rating saved!")
                                    st.session_state["recs_base"] = None
                                else:
                                    st.error(f"Error: {res['error']}")

                # Comparison bar chart
                st.markdown("---")
                st.markdown("**Sustainability Comparison Chart**")
                fig = px.bar(
                    results,
                    x="product_name",
                    y="sustainability_score",
                    color="sustainability_score",
                    color_continuous_scale=[
                        [0.00, "#e74c3c"],
                        [0.25, "#e67e22"],
                        [0.50, "#f1c40f"],
                        [0.75, "#2ecc71"],
                        [1.00, "#27ae60"],
                    ],
                    range_color=[1, 5],
                    labels={
                        "product_name":        "Product",
                        "sustainability_score": "Eco Score",
                    },
                    title=f"Eco Scores — variants of '{query}'",
                )
                fig.update_layout(
                    xaxis_tickangle=-25,
                    coloraxis_showscale=False,
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)

    # ====================================================================
    # TAB 2 — PERSONALISED CF RECOMMENDATIONS
    # ====================================================================
    with tab2:
        st.subheader("🎯 Personalised Recommendations")
        st.markdown(
            "Based on **users similar to you** · re-ranked by your eco weight "
            "(use the sidebar slider)."
        )

        uname = st.session_state["username"]
        if st.session_state["recs_user"] != uname:
            st.session_state["recs_base"] = None
            st.session_state["recs_user"] = uname

        if st.button("🔄 Generate My Recommendations", use_container_width=True):
            with st.spinner("Finding similar users and computing predictions …"):
                base = get_base_recommendations(uname, ratings_df, products_df)
            if base is None or base.empty:
                st.session_state["recs_base"] = None
                st.warning(
                    "Not enough data yet.  \n"
                    "Go to **🔍 Product Search**, rate a few products, "
                    "then click Generate again."
                )
            else:
                st.session_state["recs_base"] = base
                st.session_state["recs_user"] = uname

        base = st.session_state.get("recs_base")

        if base is not None and not base.empty:
            col_a, col_b = st.columns(2, gap="large")

            with col_a:
                st.markdown("### A) Traditional")
                st.caption(
                    "Sorted by predicted rating only — sustainability ignored.  \n"
                    "*(Same user always gets the same ranking — CF is deterministic.)*"
                )
                trad = (
                    base[["product_name", "category", "brand",
                           "price", "predicted_rating"]]
                    .sort_values("predicted_rating", ascending=False)
                    .head(5)
                    .reset_index(drop=True)
                )
                trad.index += 1
                st.dataframe(
                    trad.rename(columns={
                        "product_name":    "Product",
                        "category":        "Category",
                        "brand":           "Brand",
                        "price":           "Price (₹)",
                        "predicted_rating": "Pred. Rating",
                    }),
                    use_container_width=True,
                )
                st.metric(
                    "Avg Predicted Rating",
                    f"⭐ {trad['predicted_rating'].mean():.2f}",
                )

            with col_b:
                st.markdown("### B) Eco-Weighted")
                st.info(
                    f"Formula: `({rating_w:.1f} × Rating) + ({eco_w:.1f} × Eco Score)`  \n"
                    "← Move the sidebar slider to re-rank instantly."
                )
                sust = apply_weights(base, rating_w, eco_w, n=5)
                sd = sust[["product_name", "category",
                            "predicted_rating", "sustainability_score",
                            "final_score"]].copy()
                sd.index = range(1, len(sd) + 1)
                st.dataframe(
                    sd.rename(columns={
                        "product_name":        "Product",
                        "category":            "Category",
                        "predicted_rating":    "Pred. Rating",
                        "sustainability_score": "Eco Score",
                        "final_score":         "Final Score",
                    }),
                    use_container_width=True,
                )
                c1, c2, c3 = st.columns(3)
                c1.metric("Avg Final Score",  f"{sust['final_score'].mean():.2f}")
                c2.metric("Avg Eco Score",    f"{sust['sustainability_score'].mean():.2f}")
                c3.metric("Avg Pred. Rating", f"{sust['predicted_rating'].mean():.2f}")

            # Scatter of all candidates
            st.markdown("---")
            st.markdown("**All Candidate Products — Predicted Rating vs Eco Score**")
            fig = px.scatter(
                base,
                x="sustainability_score",
                y="predicted_rating",
                hover_name="product_name",
                color="category",
                labels={
                    "sustainability_score": "Eco Score",
                    "predicted_rating":     "Predicted Rating",
                },
                title="Your recommendation candidates",
            )
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        elif st.session_state["recs_base"] is None:
            st.info(
                "Click **Generate My Recommendations** to get started.  \n"
                "No ratings yet? Rate products in **🔍 Product Search** first."
            )

    # ====================================================================
    # TAB 3 — MY RATINGS
    # ====================================================================
    with tab3:
        st.subheader("⭐ My Ratings")
        user_ratings = get_user_ratings(st.session_state["username"])

        if not user_ratings:
            st.info(
                "You haven't rated any products yet.  \n"
                "Search for a product in **🔍 Product Search** and rate it!"
            )
        else:
            df_r = pd.DataFrame(user_ratings)
            st.markdown(f"You have rated **{len(df_r)}** products.")

            cols_map = {
                "product_name":        "Product",
                "category":            "Category",
                "brand":               "Brand",
                "sustainability_score": "Eco Score",
                "eco_label":           "Eco Label",
                "rating":              "Your Rating",
            }
            st.dataframe(
                df_r.rename(columns=cols_map)[list(cols_map.values())],
                use_container_width=True,
                hide_index=True,
            )

            fig = px.scatter(
                df_r,
                x="sustainability_score",
                y="rating",
                hover_name="product_name",
                color="category",
                labels={
                    "sustainability_score": "Eco Score",
                    "rating":              "Your Rating",
                },
                title="Your Ratings vs. Eco Score",
            )
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    # ====================================================================
    # TAB 4 — ANALYTICS
    # ====================================================================
    with tab4:
        st.subheader("📈 Platform Analytics")

        all_products = pd.DataFrame(get_all_products())

        if ratings_df.empty or all_products.empty:
            st.info("No ratings data yet.")
            return

        merged = ratings_df.merge(
            all_products[["product_id", "product_name",
                           "category", "sustainability_score"]],
            on="product_id", how="left",
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Average Rating by Category**")
            cat_avg = (
                merged.groupby("category")["rating"]
                .mean()
                .sort_values(ascending=False)
                .reset_index()
            )
            fig = px.bar(
                cat_avg, x="category", y="rating",
                color="rating", color_continuous_scale="Greens",
                labels={"category": "Category", "rating": "Avg Rating"},
            )
            fig.update_layout(
                coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("**Products per Sustainability Score**")
            eco_d = (
                all_products["sustainability_score"]
                .value_counts().sort_index().reset_index()
            )
            eco_d.columns = ["Eco Score", "Count"]
            fig = px.bar(
                eco_d, x="Eco Score", y="Count",
                color="Eco Score",
                color_continuous_scale=[
                    [0.0, "#e74c3c"], [0.25, "#e67e22"],
                    [0.5, "#f1c40f"], [0.75, "#2ecc71"], [1.0, "#27ae60"],
                ],
                range_color=[1, 5],
            )
            fig.update_layout(
                coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**Overall Rating Distribution**")
            fig = px.histogram(
                merged, x="rating", nbins=10,
                color_discrete_sequence=["#27ae60"],
                labels={"rating": "Rating", "count": "Count"},
            )
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with c4:
            st.markdown("**Avg Rating vs Eco Score**")
            er = merged.groupby("sustainability_score")["rating"].mean().reset_index()
            fig = px.line(
                er, x="sustainability_score", y="rating", markers=True,
                labels={
                    "sustainability_score": "Eco Score",
                    "rating":              "Avg Rating",
                },
                color_discrete_sequence=["#27ae60"],
            )
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("**Most Rated Products**")
        top = (
            merged.groupby("product_name")["rating"]
            .agg(["count", "mean"])
            .sort_values("count", ascending=False)
            .head(10)
            .reset_index()
        )
        top.columns = ["Product", "# Ratings", "Avg Rating"]
        top["Avg Rating"] = top["Avg Rating"].round(2)
        st.dataframe(top, use_container_width=True, hide_index=True)


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    st.set_page_config(
        page_title="Sustainable Product Recommender",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    create_tables()   # safe to call every run — uses CREATE IF NOT EXISTS
    init_session()

    if st.session_state["logged_in"]:
        show_main_app()
    else:
        show_auth_page()


if __name__ == "__main__":
    main()