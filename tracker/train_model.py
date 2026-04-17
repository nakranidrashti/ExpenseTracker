import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib

# 1️⃣ Load dataset
data = pd.read_csv("category_prediction_dataset.csv")

# 2️⃣ Input & Output
X = data["Description"]
y = data["Category"]

# 3️⃣ Text → Numbers
vectorizer = CountVectorizer()
X_vec = vectorizer.fit_transform(X)

# 4️⃣ Train model
model = MultinomialNB()
model.fit(X_vec, y)

# 5️⃣ Save model
joblib.dump(model, "expense_model.pkl")
joblib.dump(vectorizer, "vectorizer.pkl")

 print("✅ Model trained successfully!")