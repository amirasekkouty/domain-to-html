"""
Letterboxd Movie Recommender
----------------------------
Uses your exported Letterboxd ratings.csv + TMDb API to generate
personalized movie recommendations based on your highest-rated films.

SETUP
1. Install dependencies:
   pip install pandas requests python-dotenv

2. Create a .env file in the same folder:
   TMDB_API_KEY=your_api_key_here

3. Place your Letterboxd ratings.csv in the same folder

4. Run:
   python letterboxd_movie_recommender.py

OUTPUT
- recommended_movies.csv
- printed top recommendations
"""

import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

if not TMDB_API_KEY:
    raise ValueError("Missing TMDB_API_KEY. Add it to your .env file.")

BASE_URL = "https://api.themoviedb.org/3"
RATINGS_FILE = "ratings.csv"
OUTPUT_FILE = "recommended_movies.csv"
MIN_PERSONAL_RATING = 4.5  # use your favorites only
MAX_RECOMMENDATIONS = 30
REQUEST_DELAY = 0.25  # helps avoid rate limits


def tmdb_search_movie(title, year=None):
    """Find a movie by title (and optionally year)."""
    url = f"{BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "include_adult": False,
    }

    if pd.notna(year):
        params["year"] = int(year)

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    results = response.json().get("results", [])

    return results[0] if results else None



def tmdb_similar_movies(movie_id):
    """Get similar movies from TMDb."""
    url = f"{BASE_URL}/movie/{movie_id}/similar"
    params = {"api_key": TMDB_API_KEY}

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json().get("results", [])



def load_top_rated_movies():
    """Load your highest-rated Letterboxd films."""
    df = pd.read_csv(RATINGS_FILE)

    favorites = df[df["Rating"] >= MIN_PERSONAL_RATING].copy()
    favorites = favorites.sort_values("Rating", ascending=False)

    print(f"Found {len(favorites)} highly rated films (>= {MIN_PERSONAL_RATING})")
    return favorites



def build_recommendations():
    favorites = load_top_rated_movies()

    watched_titles = set(favorites["Name"].str.lower().str.strip())
    recommendation_scores = {}

    for _, row in favorites.iterrows():
        title = row["Name"]
        year = row.get("Year")
        personal_rating = row["Rating"]

        print(f"Analyzing: {title} ({year})")

        try:
            movie = tmdb_search_movie(title, year)
            if not movie:
                print(f"  -> No TMDb match found")
                continue

            similar_movies = tmdb_similar_movies(movie["id"])

            for rec in similar_movies:
                rec_title = rec.get("title", "").strip()
                if not rec_title:
                    continue

                if rec_title.lower() in watched_titles:
                    continue

                # weighted score
                score = (
                    personal_rating * 2
                    + (rec.get("vote_average", 0) / 2)
                    + (rec.get("popularity", 0) / 100)
                )

                if rec_title not in recommendation_scores:
                    recommendation_scores[rec_title] = {
                        "Title": rec_title,
                        "Year": rec.get("release_date", "")[:4],
                        "TMDb Rating": rec.get("vote_average", 0),
                        "Popularity": rec.get("popularity", 0),
                        "Recommendation Score": 0,
                        "Recommended Because": [],
                    }

                recommendation_scores[rec_title]["Recommendation Score"] += score
                recommendation_scores[rec_title]["Recommended Because"].append(title)

            time.sleep(REQUEST_DELAY)

        except Exception as e:
            print(f"  -> Error: {e}")

    results = pd.DataFrame(recommendation_scores.values())

    if results.empty:
        print("No recommendations generated.")
        return

    results["Recommended Because"] = results["Recommended Because"].apply(
        lambda x: ", ".join(sorted(set(x))[:5])
    )

    results = results.sort_values(
        "Recommendation Score", ascending=False
    ).head(MAX_RECOMMENDATIONS)

    results.to_csv(OUTPUT_FILE, index=False)

    print("\nTop Recommendations:\n")
    print(results[["Title", "Year", "Recommendation Score"]].to_string(index=False))
    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    build_recommendations()

