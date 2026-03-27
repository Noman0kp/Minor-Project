"""
Sustainable Product Recommendation System using Streamlit

This application builds a collaborative filtering recommendation system
with sustainability awareness. It recommends products based on both
predicted ratings and sustainability scores.
"""

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import os


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
    """
    # Store initial shape for logging
    initial_rows = len(df)
    
    # Remove null values
    df = df.dropna()
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['user_id', 'product_id'], keep='first')
    
    final_rows = len(df)
    rows_removed = initial_rows - final_rows
    
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
        int: Sustainability score (2-5)
    """
    category_lower = str(category).lower()
    
    # Check for high sustainability keywords
    if any(keyword in category_lower for keyword in ['eco', 'organic', 'recycled']):
        return 5
    # Check for electronics (moderate sustainability)
    elif 'electronics' in category_lower:
        return 3
    # Default score for other categories
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
        pd.DataFrame: User-item matrix where rows are users, columns are products
    """
    # Create pivot table with user_id as index, product_id as columns, rating as values
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
    # Apply cosine similarity
    user_similarity = cosine_similarity(user_item_matrix)
    user_ids = user_item_matrix.index.tolist()
    return user_similarity, user_ids


def get_traditional_recommendations(user_id, df, user_item_matrix, 
                                   user_similarity, user_ids, n_recommendations=5):
    """
    Generate traditional recommendations using collaborative filtering.
    
    Uses similar users' ratings to predict ratings for unrated items.
    
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
        # Find the index of the target user
        user_index = user_ids.index(user_id)
    except ValueError:
        return pd.DataFrame()
    
    # Get similarity scores for the target user (excluding the user itself)
    user_similarities = user_similarity[user_index]
    
    # Get unrated items for the target user
    user_ratings = user_item_matrix.iloc[user_index]
    unrated_items = user_ratings[user_ratings == 0].index.tolist()
    
    if not unrated_items:
        return pd.DataFrame()
    
    # Filter similarity scores (exclude the user itself)
    similar_user_indices = np.argsort(user_similarities)[::-1][1:6]  # Top 5 similar users
    
    # Predict ratings for unrated items
    predictions = {}
    for product_id in unrated_items:
        # Get ratings of similar users for this product
        similar_ratings = []
        similar_weights = []
        
        for idx in similar_user_indices:
            rating = user_item_matrix.iloc[idx][product_id]
            if rating > 0:  # If the similar user rated this product
                similar_ratings.append(rating)
                similar_weights.append(user_similarities[idx])
        
        if similar_ratings and similar_weights:
            # Weighted average of similar users' ratings
            predicted_rating = np.average(similar_ratings, weights=similar_weights)
            predictions[product_id] = predicted_rating
    
    # Get product information and create recommendations
    recommendations = []
    for product_id, predicted_rating in predictions.items():
        product_info = df[df['product_id'] == product_id].iloc[0]
        recommendations.append({
            'product_id': product_id,
            'product_name': product_info['product_name'],
            'category': product_info['category'],
            'predicted_rating': round(predicted_rating, 2)
        })
    
    # Sort by predicted rating and return top n
    recommendations = sorted(recommendations, key=lambda x: x['predicted_rating'], reverse=True)
    return pd.DataFrame(recommendations[:n_recommendations])


def get_sustainable_recommendations(user_id, df, user_item_matrix, 
                                   user_similarity, user_ids, n_recommendations=5,
                                   rating_weight=0.7, sustainability_weight=0.3):
    """
    Generate sustainability-aware recommendations.
    
    Combines predicted ratings and sustainability scores:
    final_score = (rating_weight * predicted_rating) + (sustainability_weight * sustainability_score)
    
    Args:
        user_id (str): Target user ID
        df (pd.DataFrame): Original dataset with sustainability_score
        user_item_matrix (pd.DataFrame): User-item rating matrix
        user_similarity (np.ndarray): User similarity matrix
        user_ids (list): List of user IDs
        n_recommendations (int): Number of recommendations to return
        rating_weight (float): Weight for predicted rating (default 0.7)
        sustainability_weight (float): Weight for sustainability score (default 0.3)
    
    Returns:
        pd.DataFrame: Recommended products with final scores
    """
    try:
        # Find the index of the target user
        user_index = user_ids.index(user_id)
    except ValueError:
        return pd.DataFrame()
    
    # Get similarity scores for the target user
    user_similarities = user_similarity[user_index]
    
    # Get unrated items for the target user
    user_ratings = user_item_matrix.iloc[user_index]
    unrated_items = user_ratings[user_ratings == 0].index.tolist()
    
    if not unrated_items:
        return pd.DataFrame()
    
    # Filter similarity scores (exclude the user itself)
    similar_user_indices = np.argsort(user_similarities)[::-1][1:6]  # Top 5 similar users
    
    # Predict ratings and calculate final scores
    recommendations = []
    for product_id in unrated_items:
        # Get ratings of similar users for this product
        similar_ratings = []
        similar_weights = []
        
        for idx in similar_user_indices:
            rating = user_item_matrix.iloc[idx][product_id]
            if rating > 0:
                similar_ratings.append(rating)
                similar_weights.append(user_similarities[idx])
        
        if similar_ratings and similar_weights:
            # Predicted rating
            predicted_rating = np.average(similar_ratings, weights=similar_weights)
            
            # Get sustainability score (normalize to 0-5 scale)
            product_info = df[df['product_id'] == product_id].iloc[0]
            sustainability_score = product_info['sustainability_score']
            
            # Normalize scores to 0-1 range for fair comparison
            normalized_predicted_rating = predicted_rating / 5.0
            normalized_sustainability_score = sustainability_score / 5.0
            
            # Calculate final score
            final_score = (rating_weight * normalized_predicted_rating) + \
                         (sustainability_weight * normalized_sustainability_score)
            final_score = round(final_score * 5, 2)  # Scale back to 0-5
            
            recommendations.append({
                'product_id': product_id,
                'product_name': product_info['product_name'],
                'category': product_info['category'],
                'predicted_rating': round(predicted_rating, 2),
                'sustainability_score': sustainability_score,
                'final_score': final_score
            })
    
    # Sort by final score and return top n
    recommendations = sorted(recommendations, key=lambda x: x['final_score'], reverse=True)
    return pd.DataFrame(recommendations[:n_recommendations])


# ============================================================================
# STREAMLIT UI
# ============================================================================

def main():
    """Main Streamlit application."""
    
    # Page configuration
    st.set_page_config(
        page_title="Sustainable Product Recommendation System",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Title and description
    st.title("🌱 Sustainable Product Recommendation System")
    st.markdown("""
    This system recommends products using collaborative filtering with 
    sustainability awareness. It balances product ratings with environmental impact.
    """)
    
    # ========================================================================
    # LOAD AND PROCESS DATA
    # ========================================================================
    
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(script_dir, 'dataset.csv')
    
    # Load dataset
    df = load_dataset(dataset_path)
    
    if df is None:
        st.error("Failed to load dataset. Please ensure 'dataset.csv' exists in the project directory.")
        return
    
    # Clean dataset
    df_clean, rows_removed = clean_dataset(df)
    
    # Add sustainability score
    df_clean = add_sustainability_score(df_clean)
    
    # Build collaborative filtering model
    user_item_matrix = build_user_item_matrix(df_clean)
    user_similarity, user_ids = calculate_user_similarity(user_item_matrix)
    
    # ========================================================================
    # SIDEBAR - USER CONTROLS
    # ========================================================================
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("Select User")
        selected_user = st.selectbox(
            "Choose a user to get recommendations:",
            options=sorted(df_clean['user_id'].unique()),
            help="Select a user ID to generate personalized recommendations"
        )
        
        st.divider()
        
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
        
        st.divider()
        
        st.subheader("Dataset Statistics")
        st.metric("Total Records", len(df_clean))
        st.metric("Total Users", df_clean['user_id'].nunique())
        st.metric("Total Products", df_clean['product_id'].nunique())
        st.metric("Rows Cleaned", rows_removed)
    
    # ========================================================================
    # MAIN CONTENT - TABS
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
            sustainability_preview = df_clean[['product_id', 'product_name', 'category', 'sustainability_score']].drop_duplicates()
            st.dataframe(sustainability_preview, use_container_width=True)
        
        st.write("**Sustainability Score Rules:**")
        rules = pd.DataFrame({
            'Category Keywords': ['eco, organic, recycled', 'electronics', 'others'],
            'Sustainability Score': [5, 3, 2]
        })
        st.table(rules)
    
    # ====== TAB 2: Recommendations ======
    with tab2:
        st.subheader(f"Recommendations for {selected_user}")
        
        # Generate recommendations button
        if st.button("🔍 Generate Recommendations", use_container_width=True):
            with st.spinner("Generating recommendations..."):
                # Get traditional recommendations
                traditional_recs = get_traditional_recommendations(
                    selected_user, df_clean, user_item_matrix, user_similarity, user_ids
                )
                
                # Get sustainable recommendations
                sustainable_recs = get_sustainable_recommendations(
                    selected_user, df_clean, user_item_matrix, user_similarity, user_ids,
                    rating_weight=rating_weight,
                    sustainability_weight=sustainability_weight
                )
                
                if traditional_recs.empty:
                    st.warning(f"No recommendations available for user {selected_user}. "
                              "The user may have already rated all available products.")
                else:
                    # Display traditional recommendations
                    st.markdown("### A) Traditional Recommendations")
                    st.markdown("*Based on user ratings and collaborative filtering*")
                    
                    if not traditional_recs.empty:
                        # Create styled dataframe for traditional recommendations
                        traditional_display = traditional_recs.copy()
                        traditional_display.columns = ['Product ID', 'Product Name', 'Category', 'Predicted Rating']
                        st.dataframe(traditional_display, use_container_width=True, hide_index=True)
                        
                        # Show summary
                        avg_rating = traditional_recs['predicted_rating'].mean()
                        st.metric("Average Predicted Rating", f"⭐ {avg_rating:.2f}")
                    
                    st.divider()
                    
                    # Display sustainable recommendations
                    st.markdown("### B) Sustainable Recommendations")
                    st.markdown("*Based on predicted ratings and sustainability impact*")
                    st.markdown(f"**Formula:** Final Score = (0.7 × Predicted Rating) + (0.3 × Sustainability Score)")
                    
                    if not sustainable_recs.empty:
                        # Create styled dataframe for sustainable recommendations
                        sustainable_display = sustainable_recs.copy()
                        sustainable_display.columns = [
                            'Product ID', 'Product Name', 'Category', 
                            'Predicted Rating', 'Sustainability', 'Final Score'
                        ]
                        st.dataframe(sustainable_display, use_container_width=True, hide_index=True)
                        
                        # Show summary statistics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            avg_final_score = sustainable_recs['final_score'].mean()
                            st.metric("Average Final Score", f"{avg_final_score:.2f}")
                        with col2:
                            avg_sustainability = sustainable_recs['sustainability_score'].mean()
                            st.metric("Average Sustainability", f"{avg_sustainability:.2f}")
                        with col3:
                            avg_predicted = sustainable_recs['predicted_rating'].mean()
                            st.metric("Average Predicted Rating", f"{avg_predicted:.2f}")
    
    # ====== TAB 3: Analytics ======
    with tab3:
        st.subheader("System Analytics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Average rating distribution
            st.write("**Average Rating by Category:**")
            category_ratings = df_clean.groupby('category')['rating'].mean().sort_values(ascending=False)
            st.bar_chart(category_ratings)
        
        with col2:
            # Sustainability score distribution
            st.write("**Sustainability Score Distribution:**")
            sustainability_dist = df_clean.groupby('sustainability_score').size()
            st.bar_chart(sustainability_dist)
        
        with col3:
            # Product per category
            st.write("**Products per Category:**")
            category_count = df_clean['category'].value_counts()
            st.bar_chart(category_count)
        
        st.divider()
        
        # User activity
        st.write("**User Activity (Ratings per User):**")
        user_activity = df_clean.groupby('user_id').size().sort_values(ascending=False)
        st.bar_chart(user_activity)


if __name__ == "__main__":
    main()
