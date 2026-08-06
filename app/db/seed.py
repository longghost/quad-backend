"""Populates the database with sample data matching the front-end's mock listings.
Usage: python -m app.db.seed
"""
from app.database import SessionLocal
from app.models import User, Category, Listing
from app.security import hash_password

SAMPLE_USERS = [
    {"full_name": "Ama Owusu", "email": "ama.owusu@knust.edu.gh", "university": "KNUST"},
    {"full_name": "Kwame Boateng", "email": "kwame.boateng@knust.edu.gh", "university": "KNUST"},
    {"full_name": "Efua Tetteh", "email": "efua.tetteh@knust.edu.gh", "university": "KNUST"},
    {"full_name": "Nana Kufuor", "email": "nana.kufuor@knust.edu.gh", "university": "KNUST"},
    {"full_name": "Admin User", "email": "admin@quad.app", "university": "KNUST", "role": "admin"},
]

SAMPLE_LISTINGS = [
    {"seller": "ama.owusu@knust.edu.gh", "category": "Textbooks", "title": "Calculus: Early Transcendentals (8th Ed)", "price": 85, "condition": "Good"},
    {"seller": "kwame.boateng@knust.edu.gh", "category": "Electronics", "title": "TI-84 Plus Graphing Calculator", "price": 180, "condition": "Like new"},
    {"seller": "efua.tetteh@knust.edu.gh", "category": "Dorm & Living", "title": "Mini Fridge — 45L, works perfectly", "price": 320, "condition": "Fair"},
    {"seller": "nana.kufuor@knust.edu.gh", "category": "Services", "title": "Statistics Tutoring — 1-on-1, per session", "price": 40, "condition": "Service"},
    {"seller": "ama.owusu@knust.edu.gh", "category": "Textbooks", "title": "Organic Chemistry Lab Manual (3rd Ed)", "price": 45, "condition": "Good"},
    {"seller": "kwame.boateng@knust.edu.gh", "category": "Textbooks", "title": "Introduction to Psychology — 12th Edition", "price": 60, "condition": "Like new"},
    {"seller": "efua.tetteh@knust.edu.gh", "category": "Textbooks", "title": "Engineering Drawing Set + Instrument Box", "price": 35, "condition": "Good"},
    {"seller": "nana.kufuor@knust.edu.gh", "category": "Textbooks", "title": "BSc Nursing Revision Notes — Full Semester (Photocopied)", "price": 25, "condition": "Good"},
    {"seller": "ama.owusu@knust.edu.gh", "category": "Electronics", "title": "Casio fx-991ES Plus Scientific Calculator", "price": 70, "condition": "Like new"},
]


def main():
    db = SessionLocal()
    try:
        password_hash = hash_password("Password123!")
        user_ids = {}

        for u in SAMPLE_USERS:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if existing:
                user_ids[u["email"]] = existing.id
                continue
            user = User(
                full_name=u["full_name"], email=u["email"], university=u["university"],
                password_hash=password_hash, role=u.get("role", "student"),
            )
            db.add(user)
            db.flush()
            user_ids[u["email"]] = user.id

        categories = {c.name: c.id for c in db.query(Category).all()}
        existing_titles = {l.title for l in db.query(Listing).all()}

        added = 0
        for l in SAMPLE_LISTINGS:
            if l["title"] in existing_titles:
                continue
            listing = Listing(
                seller_id=user_ids[l["seller"]], category_id=categories[l["category"]],
                title=l["title"], price=l["price"], currency="GHS",
                condition=l["condition"], status="active",
            )
            db.add(listing)
            added += 1

        db.commit()
        print(f"Added {added} new listing(s) (skipped {len(SAMPLE_LISTINGS) - added} already present).")
        print("Seed complete. Sample login: ama.owusu@knust.edu.gh / Password123!")
        print("Admin login: admin@quad.app / Password123!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
