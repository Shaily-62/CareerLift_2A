import pandas as pd
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load dataset from HuggingFace
ds = load_dataset("azrai99/coursera-course-dataset")
df = ds["train"].to_pandas().head(600)

# Clean dataset
df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0)
df["Level"] = df["Level"].astype(str).fillna("Beginner")

def extract_skills(skill_data):
    if isinstance(skill_data, list):
        return ", ".join(skill_data)
    elif isinstance(skill_data, str):
        return skill_data
    else:
        return ""

df["Skills"] = df["Skills"].apply(extract_skills)

courses_df = pd.DataFrame({
    "course_name": df["title"].astype(str),
    "platform": df["Organization"].fillna("Coursera").astype(str),
    "skills_taught": df["Skills"].fillna(""),
    "course_url": df["URL"].astype(str),
    "difficulty": df["Level"],
    "rating": df["rating"]
})

def recommend_courses(user_skills, top_n=5):
    if not user_skills:
        return courses_df.sort_values(by="rating", ascending=False).head(top_n)

    # convert list → string
    user_skills_str = " ".join(user_skills) if isinstance(user_skills, list) else str(user_skills)

    # TF-IDF on course skills
    vectorizer = TfidfVectorizer(stop_words="english")
    course_matrix = vectorizer.fit_transform(courses_df["skills_taught"])
    user_vec = vectorizer.transform([user_skills_str])

    # similarity
    scores = cosine_similarity(user_vec, course_matrix).flatten()
    courses_df["similarity"] = scores

    # recommend top courses
    recommended = courses_df.sort_values(by=["similarity", "rating"], ascending=False).head(top_n)
    return recommended[["course_name", "platform", "rating", "course_url", "similarity"]]
