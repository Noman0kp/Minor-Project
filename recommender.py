"""
recommender.py  —  Recommendation Engine
==========================================
Two independent recommendation strategies:

1. Collaborative Filtering (CF)
   • Finds users similar to the logged-in user via cosine similarity.
   • Predicts ratings for unrated products.
   • Split into two functions so the expensive CF step runs only once
     (cached in session_state) while weight adjustments re-rank instantly.

2. Search-Based Sustainability Recommendation  (new feature)
   • User types a product name (e.g. "laptop").
   • Returns EVERY matching product variant sorted by sustainability score.
   • Shows the eco-friendly alternative alongside the standard one, helping
     users make a greener choice for exactly what they searched for.
"""

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from database import get_all_ratings, get_all_products, search_products


# ============================================================================
# DATA LOADERS
# ============================================================================

def load_ratings_df() -> pd.DataFrame:
    """Load all ratings from the DB into a DataFrame."""
    rows = get_all_ratings()
    if not rows:
        return pd.DataFrame(columns=["username", "product_id", "rating"])
    return pd.DataFrame(rows)


def load_products_df() -> pd.DataFrame:
    """Load all products from the DB into a DataFrame."""
    rows = get_all_products()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


# ============================================================================
# COLLABORATIVE FILTERING
# ============================================================================

def _build_matrix(ratings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot the ratings table into a user-item matrix.
    Rows = usernames, Columns = product_ids, Values = ratings (0 = not rated).
    """
    return ratings_df.pivot_table(
        index="username",
        columns="product_id",
        values="rating",
        fill_value=0
    )


def get_base_recommendations(
    username: str,
    ratings_df: pd.DataFrame,
    products_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Run collaborative filtering for 'username' and return ALL candidate products
    (unrated items with a computable predicted rating).

    This is the EXPENSIVE step. Call it once and store the result in
    st.session_state["recs_base_data"].  Do NOT call it on every slider move.

    Returns a DataFrame with columns:
        product_id, product_name, category, brand, price,
        eco_label, predicted_rating, sustainability_score
    Returns an empty DataFrame if the user is unknown or has rated everything.
    """
    if ratings_df.empty or products_df.empty:
        return pd.DataFrame()

    matrix   = _build_matrix(ratings_df)
    user_ids = matrix.index.tolist()

    if username not in user_ids:
        return pd.DataFrame()

    # Cosine similarity between all users
    sim_matrix   = cosine_similarity(matrix.values)
    user_idx     = user_ids.index(username)
    user_sims    = sim_matrix[user_idx]

    # Products this user has NOT rated yet
    user_row     = matrix.iloc[user_idx]
    unrated      = user_row[user_row == 0].index.tolist()
    if not unrated:
        return pd.DataFrame()

    # Top-5 most similar OTHER users (exclude the user themselves at index 0)
    top_similar  = np.argsort(user_sims)[::-1][1:6]

    candidates = []
    for pid in unrated:
        sim_ratings  = []
        sim_weights  = []
        for idx in top_similar:
            r = matrix.iloc[idx][pid]
            if r > 0:
                sim_ratings.append(r)
                sim_weights.append(user_sims[idx])

        if not sim_ratings:
            continue   # no similar user rated this product → skip

        predicted = float(np.average(sim_ratings, weights=sim_weights))

        # Attach product metadata
        product_rows = products_df[products_df["product_id"] == pid]
        if product_rows.empty:
            continue
        p = product_rows.iloc[0]

        candidates.append({
            "product_id":          pid,
            "product_name":        p["product_name"],
            "category":            p["category"],
            "brand":               p.get("brand", ""),
            "price":               p.get("price", 0.0),
            "eco_label":           p.get("eco_label", ""),
            "predicted_rating":    round(predicted, 2),
            "sustainability_score": int(p["sustainability_score"]),
        })

    return pd.DataFrame(candidates)


def apply_weights(
    base_df: pd.DataFrame,
    rating_weight: float,
    sustainability_weight: float,
    n: int = 5,
) -> pd.DataFrame:
    """
    Re-rank the CF candidates using current slider weights and return top-n.

    This is CHEAP — just arithmetic on a small DataFrame.
    Call it on every Streamlit rerun (slider move) without re-running CF.

    Formula:
        final_score = (rating_weight      × predicted_rating    / 5)
                    + (sustainability_weight × sustainability_score / 5)
        then scaled back to 0-5.
    """
    if base_df.empty:
        return pd.DataFrame()

    df = base_df.copy()
    df["final_score"] = (
        rating_weight        * (df["predicted_rating"]     / 5.0) +
        sustainability_weight * (df["sustainability_score"] / 5.0)
    ) * 5.0
    df["final_score"] = df["final_score"].round(2)

    return (
        df.sort_values("final_score", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


# ============================================================================
# SEARCH-BASED SUSTAINABILITY RECOMMENDATION  (the new feature)
# ============================================================================

def search_and_recommend(query: str) -> pd.DataFrame:
    """
    Search for a product keyword and return ALL matching variants sorted by
    sustainability score (highest first).

    Example  —  query = "laptop":
        1. Refurbished Laptop Pro (Eco-Certified)    |  ✅ Eco Score: 5
        2. Standard Laptop                           |  🟡 Eco Score: 3
        3. High-Performance Gaming Laptop            |  🟠 Eco Score: 2

    This lets the user see the greenest version of what they want to buy.

    Args:
        query (str): Free-text search term

    Returns:
        pd.DataFrame: Matching products, sustainability_score DESC
    """
    if not query or not query.strip():
        return pd.DataFrame()

    results = search_products(query.strip())
    if not results:
        return pd.DataFrame()

    return (
        pd.DataFrame(results)
        .sort_values("sustainability_score", ascending=False)
        .reset_index(drop=True)
    )