-- =========================================================
-- Quad Marketplace — PostgreSQL schema
-- =========================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- enables fast partial-text search on listings.title

CREATE TYPE user_role AS ENUM ('student', 'admin');
CREATE TYPE listing_status AS ENUM ('active', 'sold', 'removed');
CREATE TYPE report_status AS ENUM ('open', 'in_review', 'resolved', 'dismissed');

-- ---------- Users ----------
CREATE TABLE users (
  id             SERIAL PRIMARY KEY,
  full_name      VARCHAR(120) NOT NULL,
  email          VARCHAR(160) NOT NULL UNIQUE,     -- student email
  university     VARCHAR(160) NOT NULL,
  password_hash  VARCHAR(255) NOT NULL,
  role           user_role NOT NULL DEFAULT 'student',
  avatar_url     TEXT,
  date_of_birth  DATE,
  reset_token         VARCHAR(255),
  reset_token_expires TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Categories ----------
CREATE TABLE categories (
  id    SERIAL PRIMARY KEY,
  name  VARCHAR(60) NOT NULL UNIQUE
);

-- ---------- Listings ----------
CREATE TABLE listings (
  id           SERIAL PRIMARY KEY,
  seller_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category_id  INTEGER NOT NULL REFERENCES categories(id),
  title        VARCHAR(160) NOT NULL,
  description  TEXT,
  price        NUMERIC(10,2) NOT NULL CHECK (price >= 0),
  currency     VARCHAR(6) NOT NULL DEFAULT 'GHS',
  condition    VARCHAR(30) NOT NULL,        -- e.g. Like new, Good, Fair, Service
  pickup_location VARCHAR(160),
  status       listing_status NOT NULL DEFAULT 'active',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_listings_category ON listings(category_id);
CREATE INDEX idx_listings_seller   ON listings(seller_id);
CREATE INDEX idx_listings_status   ON listings(status);
CREATE INDEX idx_listings_title_trgm ON listings USING gin (title gin_trgm_ops);

-- ---------- Listing images (a listing can have multiple photos) ----------
CREATE TABLE listing_images (
  id          SERIAL PRIMARY KEY,
  listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  url         TEXT NOT NULL,
  position    SMALLINT NOT NULL DEFAULT 0
);

-- ---------- Reviews (buyer rates a seller, optionally tied to a listing) ----------
CREATE TABLE reviews (
  id           SERIAL PRIMARY KEY,
  seller_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  reviewer_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  listing_id   INTEGER REFERENCES listings(id) ON DELETE SET NULL,
  rating       SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment      TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (seller_id, reviewer_id, listing_id)
);

CREATE INDEX idx_reviews_seller ON reviews(seller_id);

-- ---------- Messages (buyer/seller chat, grouped by listing + the two participants) ----------
CREATE TABLE messages (
  id           SERIAL PRIMARY KEY,
  listing_id   INTEGER REFERENCES listings(id) ON DELETE SET NULL,
  sender_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  receiver_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body         TEXT NOT NULL,
  read_at      TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_thread ON messages(listing_id, sender_id, receiver_id);
CREATE INDEX idx_messages_receiver ON messages(receiver_id, read_at);

-- ---------- Reports (barrier-free — no login required, per Objective 1) ----------
CREATE TABLE reports (
  id              SERIAL PRIMARY KEY,
  reference       VARCHAR(12) NOT NULL UNIQUE,   -- e.g. QD-482913
  listing_id      INTEGER REFERENCES listings(id) ON DELETE SET NULL,
  reported_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  reporter_name   VARCHAR(120),                  -- optional, no account needed
  reporter_email  VARCHAR(160),                  -- optional, for follow-up
  category        VARCHAR(60) NOT NULL,          -- e.g. Scam, Spam, Inappropriate, Other
  description     TEXT NOT NULL,
  status          report_status NOT NULL DEFAULT 'open',
  resolved_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
  resolution_note TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reports_status ON reports(status);

-- ---------- Transactions (Paystack payments) ----------
CREATE TYPE transaction_status AS ENUM ('pending', 'success', 'failed');

CREATE TABLE transactions (
  id                  SERIAL PRIMARY KEY,
  listing_id          INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
  buyer_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  seller_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  amount              NUMERIC(10,2) NOT NULL,
  currency            VARCHAR(6) NOT NULL DEFAULT 'GHS',
  paystack_reference  VARCHAR(100) NOT NULL UNIQUE,
  status              transaction_status NOT NULL DEFAULT 'pending',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_transactions_listing ON transactions(listing_id);
CREATE INDEX idx_transactions_buyer ON transactions(buyer_id);

-- ---------- Seed categories (matches front-end mock data) ----------
INSERT INTO categories (name) VALUES
  ('Textbooks'), ('Electronics'), ('Dorm & Living'), ('Clothing'), ('Services');
