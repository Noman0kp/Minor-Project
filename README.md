📘 Sustainable Product Recommendation System for E-Commerce
📌 Project Overview

This project presents a Sustainable Product Recommendation System that enhances traditional e-commerce recommendations by incorporating environmental sustainability as a decision factor.

Unlike conventional systems that focus only on user preferences and product popularity, this system integrates a sustainability score to promote responsible consumption, aligned with SDG 12 (Responsible Consumption and Production).

🎯 Objectives
To develop a recommendation system based on user preferences
To integrate sustainability scoring into recommendations
To compare traditional vs sustainable recommendations
To promote eco-friendly product choices

🚀 Features
✔ User-based collaborative filtering
✔ Cosine similarity for user similarity calculation
✔ Sustainability score integration (rule-based)
✔ Hybrid recommendation model (preference + sustainability)
✔ Adjustable weight parameter (alpha)
✔ Interactive web interface using Streamlit
✔ Dataset preview and analytics
✔ Comparison of recommendation results

🧠 Methodology
1️⃣ Data Processing
Load dataset (CSV format)
Clean missing values and duplicates
Structure data into user-product format

2️⃣ Recommendation System
Use collaborative filtering
Compute similarity using cosine similarity
Generate predicted ratings

3️⃣ Sustainability Integration
Each product is assigned a sustainability score:

Category Type	                              Score
Eco-friendly / Organic / Recycled	            5
Electronics	                                  3
Others	                                      2

4️⃣ Final Recommendation Formula

Final Score =
(α × User Preference Score) + ((1 − α) × Sustainability Score)

Where:
α (alpha) controls balance between personalization and sustainability

🛠 Tech Stack
Language: Python
Libraries:
Pandas (data handling)
NumPy (numerical operations)
Scikit-learn (cosine similarity)
Framework: Streamlit (web interface)

📂 Project Structure
├── app.py              # Main Streamlit application
├── dataset.csv         # Input dataset
├── requirements.txt    # Required libraries
└── README.md           # Project documentation

▶️ How to Run the Project
Step 1: Install dependencies
pip install pandas numpy scikit-learn streamlit

Step 2: Run the application
streamlit run app.py

Step 3:
Open the browser at:
http://localhost:8501

📊 Dataset Description
The dataset contains:

User ID
Product ID
Product Name
Category
Rating

Currently, a synthetic dataset is used for prototype demonstration.

🌍 SDG Alignment

This project aligns with:

SDG 12 – Responsible Consumption and Production

It promotes:

Eco-friendly product visibility
Sustainable consumer behavior
Reduced environmental impact

⚠️ Limitations
Uses synthetic dataset
Sustainability scoring is rule-based
No real-time user data
Not integrated with full e-commerce platform

🔮 Future Scope
Use real-world datasets (Kaggle / industry data)
Improve sustainability scoring using ML or external APIs
Integrate with full e-commerce systems
Add advanced recommendation techniques (Hybrid / Deep Learning)
Deploy as a scalable web application

📚 References
Ricci, F., Rokach, L., Shapira, B. – Recommender Systems Handbook, Springer
Felfernig, A., et al. – Recommender Systems for Sustainability, Frontiers in Big Data
Koenigstein, N., et al. – Towards Responsible Recommender Systems, ACM RecSys

👨‍💻 Author
Your Name
B.Tech Computer Science
💡 Final Note

This project demonstrates how machine learning systems can be extended to support sustainability goals, bridging the gap between technology and environmental responsibility.
