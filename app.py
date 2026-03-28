"""
Sustainable Product Recommendation System using Streamlit
with User Authentication System

This application builds a collaborative filtering recommendation system
with sustainability awareness. It recommends products based on both
predicted ratings and sustainability scores.

Authentication:
- Predefined user dictionary (prototype only, not production-level)
- Session-based login tracking via st.session_state
- Logout support
- Simulated "Forgot Password" flow
"""

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import os


# ============================================================================
# AUTHENTICATION - USER STORE (Prototype: replace with DB in production)
# ============================================================================

# Predefined user credentials dictionary.
# In a real application, passwords would be hashed and stored in a database.
USERS = {
    "user1": {"password": "password1", "email": "user1@example.com"},
    "user2": {"password": "password2", "email": "user2@example.com"},
    "admin": {"password": "admin123",  "email": "admin@example.com"},
}


# ============================================================================
# AUTHENTICATION - SESSION STATE INITIALISATION
# ============================================================================

def init_session_state():
    """
    Initialise all session_state keys used by the auth system and recs cache.
    Called once at the very top of main() so every key always exists.
    """
    defaults = {
        "logged_in":       False,   # Is the user currently authenticated?
        "username":        "",      # Username of the logged-in user
        "show_forgot_pw":  False,   # Toggle the Forgot Password form
        # ---- Recommendation cache ----
        # Stores raw candidate data (predicted_rating + sustainability_score)
        # so weights can be re-applied live without re-running the CF algorithm.
        "recs_base_data":  None,    # pd.DataFrame of all scoreable candidates
        "recs_for_user":   "",      # Which user the cached data belongs to
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================================
# AUTHENTICATION - CORE LOGIC
# ============================================================================

def authenticate(username: str, password: str) -> bool:
    """
    Validate username and password against the USERS dictionary.

    Args:
        username (str): Entered username
        password (str): Entered password

    Returns:
        bool: True if credentials are valid, False otherwise
    """
    user = USERS.get(username)
    if user and user["password"] == password:
        return True
    return False


def login(username: str):
    """
    Mark the user as logged in in session_state.

    Args:
        username (str): Validated username
    """
    st.session_state["logged_in"] = True
    st.session_state["username"] = username
    st.session_state["show_forgot_pw"] = False


def logout():
    """
    Clear auth-related session state to log the user out.
    Streamlit will re-render and show the login page automatically.
    """
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["show_forgot_pw"] = False


# ============================================================================
# AUTHENTICATION - LOGIN PAGE UI
# ============================================================================

def show_login_page():
    """
    Render the login page.

    Behaviour:
    - Shows a username / password form.
    - On success, calls login() and triggers a rerun.
    - On failure, shows an error message.
    - Provides a 'Forgot Password?' toggle that reveals the reset form.
    """

    # ---------- Page layout ----------
    # Centre the form using three columns (wide sides are empty)
    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.markdown("## 🌱 Sustainable Product Recommender")
        st.markdown("### 🔐 Login")
        st.markdown("---")

        # ---------- Login form ----------
        # Using st.form prevents Streamlit from re-running on every keystroke
        with st.form(key="login_form"):
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                help="Use one of the predefined usernames: user1, user2, admin"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )
            submit = st.form_submit_button("Login", use_container_width=True)

        # ---------- Handle login submission ----------
        if submit:
            if not username or not password:
                st.error("⚠️ Please enter both username and password.")
            elif authenticate(username, password):
                # Valid credentials → log the user in and reload the page
                login(username)
                st.success("✅ Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("❌ Invalid username or password. Please try again.")

        st.markdown("---")

        # ---------- Forgot Password toggle ----------
        forgot_btn_label = (
            "🔼 Hide Forgot Password"
            if st.session_state["show_forgot_pw"]
            else "🔑 Forgot Password?"
        )
        if st.button(forgot_btn_label, use_container_width=True):
            # Toggle the Forgot Password section visibility
            st.session_state["show_forgot_pw"] = not st.session_state["show_forgot_pw"]
            st.rerun()

        # ---------- Forgot Password form ----------
        if st.session_state["show_forgot_pw"]:
            show_forgot_password_section()


def show_forgot_password_section():
    """
    Render the Forgot Password section below the login form.

    Behaviour:
    - Accepts a username or email input.
    - Simulates sending a password reset link (no real email is sent).
    - Shows a success banner as confirmation.
    """
    st.markdown("#### 📧 Reset Your Password")
    st.info("Enter your username or registered email and we'll send you a reset link.")

    with st.form(key="forgot_pw_form"):
        identifier = st.text_input(
            "Username or Email",
            placeholder="e.g. user1  or  user1@example.com"
        )
        reset_submit = st.form_submit_button("Send Reset Link", use_container_width=True)

    if reset_submit:
        if not identifier:
            st.warning("⚠️ Please enter your username or email.")
        else:
            # Check if the identifier matches any known user or email
            matched = False
            for uname, info in USERS.items():
                if identifier == uname or identifier == info["email"]:
                    matched = True
                    display_email = info["email"]
                    break

            if matched:
                # Simulate sending a reset link
                st.success(
                    f"✅ Password reset link has been sent to **{display_email}** (simulation). "
                    "Please check your inbox."
                )
            else:
                # Even for unknown identifiers, show a generic message
                # (avoids leaking which usernames/emails exist — good security practice)
                st.success(
                    "✅ If an account with that username/email exists, "
                    "a reset link has been sent (simulation)."
                )


# ============================================================================
# HELPER FUNCTIONS - DATA LOADING AND CLEANING
# ============================================================================

@st.cache_data
def load_dataset(file_path):
    """
    Load the dataset from a CSV file.

    Args:
        file_path (str): Path to the CSV file

    Returns:
        pd.DataFrame: Loaded dataset
    """
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        st.error(f"Dataset file not found at {file_path}")
        return None


def clean_dataset(df):
    """
    Clean the dataset by removing null values and duplicates.

    Args:
        df (pd.DataFrame): Input dataset

    Returns:
        pd.DataFrame: Cleaned dataset
        int: Number of rows removed
    """
    initial_rows = len(df)
    df = df.dropna()
    df = df.drop_duplicates(subset=['user_id', 'product_id'], keep='first')
    rows_removed = initial_rows - len(df)
    return df, rows_removed


# ============================================================================
# SUSTAINABILITY SCORING
# ============================================================================

def calculate_sustainability_score(category):
    """
    Calculate sustainability score based on product category.

    Rules:
    - Eco-Friendly keywords (eco, organic, recycled) → score = 5
    - Electronics → score = 3
    - Others → score = 2

    Args:
        category (str): Product category

    Returns:
        int: Sustainability score (2–5)
    """
    category_lower = str(category).lower()
    if any(keyword in category_lower for keyword in ['eco', 'organic', 'recycled']):
        return 5
    elif 'electronics' in category_lower:
        return 3
    else:
        return 2


def add_sustainability_score(df):
    """
    Add sustainability_score column to the dataset.

    Args:
        df (pd.DataFrame): Input dataset

    Returns:
        pd.DataFrame: Dataset with sustainability_score column
    """
    df['sustainability_score'] = df['category'].apply(calculate_sustainability_score)
    return df


# ============================================================================
# COLLABORATIVE FILTERING RECOMMENDATION ENGINE
# ============================================================================

def build_user_item_matrix(df):
    """
    Build a user-item rating matrix for collaborative filtering.

    Args:
        df (pd.DataFrame): Dataset with user_id, product_id, and rating

    Returns:
        pd.DataFrame: User-item matrix
    """
    user_item_matrix = df.pivot_table(
        index='user_id',
        columns='product_id',
        values='rating',
        fill_value=0
    )
    return user_item_matrix


def calculate_user_similarity(user_item_matrix):
    """
    Calculate similarity between users using cosine similarity.

    Args:
        user_item_matrix (pd.DataFrame): User-item rating matrix

    Returns:
        np.ndarray: User similarity matrix
        list: User IDs corresponding to matrix rows
    """
    user_similarity = cosine_similarity(user_item_matrix)
    user_ids = user_item_matrix.index.tolist()
    return user_similarity, user_ids


def get_traditional_recommendations(user_id, df, user_item_matrix,
                                    user_similarity, user_ids, n_recommendations=5):
    """
    Generate traditional recommendations using collaborative filtering.

    Args:
        user_id (str): Target user ID
        df (pd.DataFrame): Original dataset
        user_item_matrix (pd.DataFrame): User-item rating matrix
        user_similarity (np.ndarray): User similarity matrix
        user_ids (list): List of user IDs
        n_recommendations (int): Number of recommendations to return

    Returns:
        pd.DataFrame: Recommended products with predicted ratings
    """
    try:
        user_index = user_ids.index(user_id)
    except ValueError:
        return pd.DataFrame()

    user_similarities = user_similarity[user_index]
    user_ratings = user_item_matrix.iloc[user_index]
    unrated_items = user_ratings[user_ratings == 0].index.tolist()

    if not unrated_items:
        return pd.DataFrame()

    similar_user_indices = np.argsort(user_similarities)[::-1][1:6]

    predictions = {}
    for product_id in unrated_items:
        similar_ratings = []
        similar_weights = []
        for idx in similar_user_indices:
            rating = user_item_matrix.iloc[idx][product_id]
            if rating > 0:
                similar_ratings.append(rating)
                similar_weights.append(user_similarities[idx])
        if similar_ratings and similar_weights:
            predicted_rating = np.average(similar_ratings, weights=similar_weights)
            predictions[product_id] = predicted_rating

    recommendations = []
    for product_id, predicted_rating in predictions.items():
        product_info = df[df['product_id'] == product_id].iloc[0]
        recommendations.append({
            'product_id': product_id,
            'product_name': product_info['product_name'],
            'category': product_info['category'],
            'predicted_rating': round(predicted_rating, 2)
        })

    recommendations = sorted(recommendations, key=lambda x: x['predicted_rating'], reverse=True)
    return pd.DataFrame(recommendations[:n_recommendations])


def get_base_recommendations(user_id, df, user_item_matrix, user_similarity, user_ids):
    """
    Compute predicted ratings and sustainability scores for all unrated products.

    This is the EXPENSIVE step (collaborative filtering). Call it once and cache
    the result in session_state. Weights are NOT applied here — use
    apply_weights_to_recs() to rank the returned data.

    Args:
        user_id (str): Target user ID
        df (pd.DataFrame): Dataset with sustainability_score column
        user_item_matrix (pd.DataFrame): User-item rating matrix
        user_similarity (np.ndarray): Cosine similarity matrix
        user_ids (list): Ordered list of user IDs matching matrix rows

    Returns:
        pd.DataFrame: One row per scoreable unrated product, columns:
                      product_id, product_name, category,
                      predicted_rating, sustainability_score
                      Returns empty DataFrame if user not found or no unrated items.
    """
    try:
        user_index = user_ids.index(user_id)
    except ValueError:
        return pd.DataFrame()

    user_similarities  = user_similarity[user_index]
    user_ratings       = user_item_matrix.iloc[user_index]
    unrated_items      = user_ratings[user_ratings == 0].index.tolist()

    if not unrated_items:
        return pd.DataFrame()

    # Top-5 most similar OTHER users
    similar_user_indices = np.argsort(user_similarities)[::-1][1:6]

    candidates = []
    for product_id in unrated_items:
        similar_ratings = []
        similar_weights = []
        for idx in similar_user_indices:
            rating = user_item_matrix.iloc[idx][product_id]
            if rating > 0:
                similar_ratings.append(rating)
                similar_weights.append(user_similarities[idx])

        if similar_ratings and similar_weights:
            predicted_rating  = np.average(similar_ratings, weights=similar_weights)
            product_info      = df[df['product_id'] == product_id].iloc[0]
            candidates.append({
                'product_id':          product_id,
                'product_name':        product_info['product_name'],
                'category':            product_info['category'],
                'predicted_rating':    round(predicted_rating, 2),
                'sustainability_score': product_info['sustainability_score'],
            })

    return pd.DataFrame(candidates)


def apply_weights_to_recs(base_df: pd.DataFrame, rating_weight: float,
                           sustainability_weight: float, n: int = 5) -> pd.DataFrame:
    """
    Apply rating/sustainability weights to pre-computed candidate data and
    return the top-n products sorted by final_score.

    This is CHEAP — no collaborative filtering is re-run. Call it every time
    the slider moves to get an instant re-ranking.

    Args:
        base_df (pd.DataFrame): Output of get_base_recommendations()
        rating_weight (float): Weight for predicted rating (0–1)
        sustainability_weight (float): Weight for sustainability score (0–1)
        n (int): Number of top results to return

    Returns:
        pd.DataFrame: Top-n rows with an added 'final_score' column
    """
    if base_df.empty:
        return pd.DataFrame()

    df = base_df.copy()

    # Normalise both scores to 0–1, combine, then scale back to 0–5
    df['final_score'] = (
        rating_weight       * (df['predicted_rating']    / 5.0) +
        sustainability_weight * (df['sustainability_score'] / 5.0)
    ) * 5

    df['final_score'] = df['final_score'].round(2)

    return df.sort_values('final_score', ascending=False).head(n).reset_index(drop=True)


# ============================================================================
# MAIN RECOMMENDATION APP (shown only after login)
# ============================================================================

def show_main_app():
    """
    Render the full Sustainable Product Recommendation System.
    This function is only called when the user is authenticated.
    """

    # ---- Page header ----
    st.title("🌱 Sustainable Product Recommendation System")
    st.markdown(
        "This system recommends products using collaborative filtering with "
        "sustainability awareness. It balances product ratings with environmental impact."
    )

    # ========================================================================
    # LOAD AND PROCESS DATA
    # ========================================================================

    script_dir   = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(script_dir, 'dataset.csv')

    df = load_dataset(dataset_path)
    if df is None:
        st.error("Failed to load dataset. Please ensure 'dataset.csv' exists in the project directory.")
        return

    df_clean, rows_removed = clean_dataset(df)
    df_clean = add_sustainability_score(df_clean)

    user_item_matrix           = build_user_item_matrix(df_clean)
    user_similarity, user_ids  = calculate_user_similarity(user_item_matrix)

    # ========================================================================
    # SIDEBAR – USER CONTROLS + LOGOUT
    # ========================================================================

    with st.sidebar:
        st.header("⚙️ Configuration")

        # ---- Logged-in user info + logout ----
        st.markdown(f"👤 **Logged in as:** `{st.session_state['username']}`")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()   # Return to login page immediately

        st.divider()

        # ---- User selector ----
        st.subheader("Select User")
        selected_user = st.selectbox(
            "Choose a user to get recommendations:",
            options=sorted(df_clean['user_id'].unique()),
            help="Select a user ID to generate personalised recommendations"
        )

        # If the user changed, clear cached recommendations so stale
        # results from a previous user are never displayed.
        if selected_user != st.session_state["recs_for_user"]:
            st.session_state["recs_base_data"] = None
            st.session_state["recs_for_user"]  = selected_user

        st.divider()

        # ---- Algorithm weights ----
        st.subheader("Algorithm Weights")
        rating_weight = st.slider(
            "Rating Weight (for sustainable recommendations):",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Higher weight gives more importance to predicted ratings"
        )
        sustainability_weight = 1.0 - rating_weight
        st.metric("Sustainability Weight:", f"{sustainability_weight:.1f}")

        # Live re-ranking hint — only shown when cached data exists
        if st.session_state["recs_base_data"] is not None:
            st.caption("⚡ Sustainable scores update live as you move the slider.")

        st.divider()

        # ---- Dataset statistics ----
        st.subheader("Dataset Statistics")
        st.metric("Total Records",  len(df_clean))
        st.metric("Total Users",    df_clean['user_id'].nunique())
        st.metric("Total Products", df_clean['product_id'].nunique())
        st.metric("Rows Cleaned",   rows_removed)

    # ========================================================================
    # MAIN CONTENT – TABS
    # ========================================================================

    tab1, tab2, tab3 = st.tabs(
        ["📊 Dataset Preview", "🎯 Recommendations", "📈 Analytics"]
    )

    # ====== TAB 1: Dataset Preview ======
    with tab1:
        st.subheader("Dataset Overview")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Raw Dataset Preview:**")
            st.dataframe(df_clean.head(10), use_container_width=True)

        with col2:
            st.write("**Sustainability Score Distribution:**")
            sustainability_preview = df_clean[
                ['product_id', 'product_name', 'category', 'sustainability_score']
            ].drop_duplicates()
            st.dataframe(sustainability_preview, use_container_width=True)

        st.write("**Sustainability Score Rules:**")
        rules = pd.DataFrame({
            'Category Keywords':   ['eco, organic, recycled', 'electronics', 'others'],
            'Sustainability Score': [5, 3, 2]
        })
        st.table(rules)

    # ====== TAB 2: Recommendations ======
    with tab2:
        st.subheader(f"Recommendations for {selected_user}")

        # ----------------------------------------------------------------
        # GENERATE button — runs the expensive CF step ONCE per user,
        # then stores raw candidate data in session_state.
        # Subsequent slider moves re-rank the cached data instantly.
        # ----------------------------------------------------------------
        if st.button("🔍 Generate Recommendations", use_container_width=True):
            with st.spinner("Running collaborative filtering..."):
                base_data = get_base_recommendations(
                    selected_user, df_clean, user_item_matrix, user_similarity, user_ids
                )
            if base_data.empty:
                st.session_state["recs_base_data"] = None
                st.warning(
                    f"No recommendations available for **{selected_user}**. "
                    "This user may have already rated all available products."
                )
            else:
                # Cache the raw predictions — weights applied separately below
                st.session_state["recs_base_data"] = base_data
                st.session_state["recs_for_user"]  = selected_user

        # ----------------------------------------------------------------
        # DISPLAY — runs on every Streamlit rerun (button click OR slider
        # move). Always reads from session_state so the view stays fresh.
        # ----------------------------------------------------------------
        base_data = st.session_state.get("recs_base_data")

        if base_data is not None:

            # ---- A) Traditional Recommendations ----
            # Sorted purely by predicted_rating — weights have no effect here.
            st.markdown("### A) Traditional Recommendations")
            st.markdown("*Based on user ratings and collaborative filtering*")
            st.caption("ℹ️ This section is deterministic — same user always gets the same ranking because the algorithm is not random.")

            traditional_recs = (
                base_data[['product_id', 'product_name', 'category', 'predicted_rating']]
                .sort_values('predicted_rating', ascending=False)
                .head(5)
                .reset_index(drop=True)
            )
            traditional_display = traditional_recs.copy()
            traditional_display.columns = ['Product ID', 'Product Name', 'Category', 'Predicted Rating']
            st.dataframe(traditional_display, use_container_width=True, hide_index=True)
            st.metric("Average Predicted Rating", f"⭐ {traditional_recs['predicted_rating'].mean():.2f}")

            st.divider()

            # ---- B) Sustainable Recommendations ----
            # Re-ranked LIVE using current slider values — no re-click needed.
            st.markdown("### B) Sustainable Recommendations")
            st.markdown("*Based on predicted ratings and sustainability impact*")
            st.info(
                f"**Formula:** Final Score = "
                f"(**{rating_weight:.1f}** × Predicted Rating) + "
                f"(**{sustainability_weight:.1f}** × Sustainability Score)  "
                f"← updates instantly as you move the slider"
            )

            sustainable_recs = apply_weights_to_recs(
                base_data, rating_weight, sustainability_weight, n=5
            )

            sustainable_display = sustainable_recs[
                ['product_id', 'product_name', 'category',
                 'predicted_rating', 'sustainability_score', 'final_score']
            ].copy()
            sustainable_display.columns = [
                'Product ID', 'Product Name', 'Category',
                'Predicted Rating', 'Sustainability', 'Final Score'
            ]
            st.dataframe(sustainable_display, use_container_width=True, hide_index=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Avg Final Score",        f"{sustainable_recs['final_score'].mean():.2f}")
            with col2:
                st.metric("Avg Sustainability",      f"{sustainable_recs['sustainability_score'].mean():.2f}")
            with col3:
                st.metric("Avg Predicted Rating",    f"{sustainable_recs['predicted_rating'].mean():.2f}")

    # ====== TAB 3: Analytics ======
    with tab3:
        st.subheader("System Analytics")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**Average Rating by Category:**")
            st.bar_chart(df_clean.groupby('category')['rating'].mean().sort_values(ascending=False))
        with col2:
            st.write("**Sustainability Score Distribution:**")
            st.bar_chart(df_clean.groupby('sustainability_score').size())
        with col3:
            st.write("**Products per Category:**")
            st.bar_chart(df_clean['category'].value_counts())

        st.divider()

        st.write("**User Activity (Ratings per User):**")
        st.bar_chart(df_clean.groupby('user_id').size().sort_values(ascending=False))


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """
    Application entry point.

    Flow:
    1. Configure the Streamlit page (must be the very first st call).
    2. Initialise session_state keys.
    3. Route to login page or main app based on login status.
    """

    # Step 1 – Page config (must come before any other st.* call)
    st.set_page_config(
        page_title="Sustainable Product Recommendation System",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Step 2 – Ensure all session_state keys exist
    init_session_state()

    # Step 3 – Route based on authentication status
    if st.session_state["logged_in"]:
        # User is authenticated → show the recommendation system
        show_main_app()
    else:
        # User is not authenticated → show the login page
        show_login_page()


if __name__ == "__main__":
    main()