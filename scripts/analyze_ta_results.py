"""
Marcus - Analyse des résultats Tactical Arbitrage (Castorama -> Amazon.fr)
Filtre, score et classe les opportunités d'arbitrage.
"""
import pandas as pd
import re
import sys

CSV_PATH = r"C:\DEV\SWITAA\CSV\tacticalarbitrage_1773213484.csv"
OUTPUT_PATH = r"C:\DEV\SWITAA\CSV\marcus_opportunities_ranked.csv"

def clean_currency(val):
    if pd.isna(val) or val == "":
        return 0.0
    s = str(val).replace("€", "").replace(",", ".").replace("\xa0", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

def clean_pct(val):
    if pd.isna(val) or val == "":
        return 0.0
    s = str(val).replace("%", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

def clean_int(val):
    if pd.isna(val) or val == "":
        return 0
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return 0

print("=" * 70)
print("MARCUS - ANALYSE DES OPPORTUNITES CASTORAMA -> AMAZON.FR")
print("=" * 70)

# --- ETAPE 1 : Chargement ---
df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
print(f"\n[1] CHARGEMENT : {len(df)} produits charges")
print(f"    Colonnes : {len(df.columns)}")

# --- ETAPE 2 : Nettoyage ---
df["price_source"] = df["Price"].apply(clean_currency)
df["price_amazon"] = df["Amazon Buy Box Price"].apply(clean_currency)
df["profit"] = df["Gross Profit"].apply(clean_currency)
df["roi"] = df["Gross ROI"].apply(clean_pct)
df["monthly_sales"] = df["Estimated Monthly Sales"].apply(clean_int)
df["num_sellers"] = df["# Selling 'New'"].apply(clean_int)
df["fba_sellers"] = df["Competitive FBA Sellers"].apply(clean_int)
df["sales_rank"] = df["Sales Rank"].apply(clean_int)
df["reviews"] = df["Reviews"].apply(clean_int)
df["rating"] = df["Rating"].apply(lambda x: float(x) if pd.notna(x) and x != "" else 0.0)
df["match_quality"] = df["Match Quality"].apply(clean_int)
df["variations"] = df["Variations"].apply(clean_int)
df["profit_margin"] = df["Profit Margin"].apply(clean_pct)
df["monthly_profit_per_seller"] = df["Estimated Monthly Profit per Seller"].apply(clean_currency)
df["monthly_profit_per_fba"] = df["Estimated Monthly Profit per FBA Seller"].apply(clean_currency)
df["amazon_in_stock_30d"] = df["Amazon In Stock (30 days)"].apply(clean_int)

dupes = df.duplicated(subset=["ASIN"], keep="first").sum()
df = df.drop_duplicates(subset=["ASIN"], keep="first")
print(f"\n[2] NETTOYAGE : {dupes} doublons supprimes -> {len(df)} produits uniques")

# --- ETAPE 3 : Filtrage IP CLAIM / Marques a risque ---
ip_risk_brands = [
    "hansgrohe", "grohe", "lego", "dyson", "nike", "adidas",
    "philips", "bosch", "siemens", "apple", "samsung", "sony",
    "bose", "dewalt", "makita", "stanley", "black+decker",
]
df["brand_lower"] = df["Brand"].fillna("").str.lower().str.strip()
df["ip_risk"] = df["brand_lower"].apply(
    lambda b: any(risk in b for risk in ip_risk_brands)
)
ip_count = df["ip_risk"].sum()
print(f"\n[3] FILTRE IP/MARQUES : {ip_count} produits de marques a risque IP identifies")

# --- ETAPE 4 : Filtrage Amazon vendeur ---
df["amazon_is_seller"] = df["Amazon Sells and In Stock"].fillna("").str.lower().str.contains("in stock")
amazon_seller_count = df["amazon_is_seller"].sum()
print(f"\n[4] FILTRE AMAZON VENDEUR : {amazon_seller_count} produits ou Amazon est vendeur et en stock")

# --- ETAPE 5 : Filtrage viabilite ---
print(f"\n[5] FILTRE VIABILITE :")

df_viable = df.copy()
n0 = len(df_viable)

# 5a. Source en stock
df_viable = df_viable[df_viable["In Stock"].fillna("").str.lower() == "yes"]
print(f"    Source en stock       : {n0} -> {len(df_viable)} (-{n0 - len(df_viable)})")
n0 = len(df_viable)

# 5b. Match quality >= 80
df_viable = df_viable[df_viable["match_quality"] >= 80]
print(f"    Match quality >= 80   : {n0} -> {len(df_viable)} (-{n0 - len(df_viable)})")
n0 = len(df_viable)

# 5c. Prix source > 5 EUR (produits trop cheap = pas rentable)
df_viable = df_viable[df_viable["price_source"] >= 5]
print(f"    Prix source >= 5 EUR  : {n0} -> {len(df_viable)} (-{n0 - len(df_viable)})")
n0 = len(df_viable)

# 5d. Profit > 3 EUR (sinon pas assez de marge)
df_viable = df_viable[df_viable["profit"] >= 3]
print(f"    Profit >= 3 EUR       : {n0} -> {len(df_viable)} (-{n0 - len(df_viable)})")
n0 = len(df_viable)

# 5e. ROI >= 20%
df_viable = df_viable[df_viable["roi"] >= 20]
print(f"    ROI >= 20%            : {n0} -> {len(df_viable)} (-{n0 - len(df_viable)})")
n0 = len(df_viable)

# 5f. Ventes mensuelles estimees > 0
df_viable = df_viable[df_viable["monthly_sales"] > 0]
print(f"    Ventes mensuelles > 0 : {n0} -> {len(df_viable)} (-{n0 - len(df_viable)})")
n0 = len(df_viable)

# 5g. Exclure Amazon vendeur
df_viable = df_viable[~df_viable["amazon_is_seller"]]
print(f"    Amazon pas vendeur    : {n0} -> {len(df_viable)} (-{n0 - len(df_viable)})")
n0 = len(df_viable)

# 5h. Pas trop de vendeurs (< 30)
df_viable = df_viable[df_viable["num_sellers"] < 30]
print(f"    Nb vendeurs < 30      : {n0} -> {len(df_viable)} (-{n0 - len(df_viable)})")
n0 = len(df_viable)

print(f"\n    --> {len(df_viable)} produits viables apres filtrage")

# Separer IP risk vs safe
df_safe = df_viable[~df_viable["ip_risk"]].copy()
df_iprisk = df_viable[df_viable["ip_risk"]].copy()
print(f"    --> {len(df_safe)} produits SAFE (pas de risque IP)")
print(f"    --> {len(df_iprisk)} produits avec RISQUE IP (a verifier)")

# --- ETAPE 6 : Scoring ---
print(f"\n[6] SCORING :")

def score_product(row):
    s = 0
    # ROI (max 25 pts)
    if row["roi"] >= 100: s += 25
    elif row["roi"] >= 60: s += 20
    elif row["roi"] >= 40: s += 15
    elif row["roi"] >= 30: s += 10
    else: s += 5

    # Profit absolu (max 25 pts)
    if row["profit"] >= 20: s += 25
    elif row["profit"] >= 10: s += 20
    elif row["profit"] >= 7: s += 15
    elif row["profit"] >= 5: s += 10
    else: s += 5

    # Ventes mensuelles (max 20 pts) - scalabilite
    if row["monthly_sales"] >= 100: s += 20
    elif row["monthly_sales"] >= 50: s += 15
    elif row["monthly_sales"] >= 20: s += 12
    elif row["monthly_sales"] >= 10: s += 8
    elif row["monthly_sales"] >= 5: s += 5
    else: s += 2

    # Competition (max 15 pts) - moins de vendeurs = mieux
    if row["num_sellers"] <= 3: s += 15
    elif row["num_sellers"] <= 5: s += 12
    elif row["num_sellers"] <= 10: s += 8
    elif row["num_sellers"] <= 15: s += 5
    else: s += 2

    # Taille produit (max 10 pts)
    size = str(row.get("Product Size", "")).lower()
    if "small" in size: s += 10
    elif "standard" in size: s += 7
    elif "large standard" in size: s += 5
    elif "oversize" in size: s += 2

    # Profit mensuel par vendeur (max 5 pts)
    if row["monthly_profit_per_seller"] >= 500: s += 5
    elif row["monthly_profit_per_seller"] >= 200: s += 4
    elif row["monthly_profit_per_seller"] >= 100: s += 3
    elif row["monthly_profit_per_seller"] >= 50: s += 2
    else: s += 1

    return s

df_safe["score"] = df_safe.apply(score_product, axis=1)
df_safe = df_safe.sort_values("score", ascending=False)

if len(df_iprisk) > 0:
    df_iprisk["score"] = df_iprisk.apply(score_product, axis=1)
    df_iprisk = df_iprisk.sort_values("score", ascending=False)

print(f"    Scoring applique sur {len(df_safe)} produits SAFE")
if len(df_safe) > 0:
    print(f"    Score moyen : {df_safe['score'].mean():.1f} / 100")
    print(f"    Score max   : {df_safe['score'].max()}")
    print(f"    Score min   : {df_safe['score'].min()}")

# --- ETAPE 7 : Resultats ---
print(f"\n{'=' * 70}")
print("RESULTATS FINAUX")
print("=" * 70)

cols_export = [
    "ASIN", "Brand", "Title", "Amazon Title", "Amazon Category",
    "price_source", "price_amazon", "profit", "roi", "profit_margin",
    "monthly_sales", "num_sellers", "fba_sellers",
    "monthly_profit_per_seller", "monthly_profit_per_fba",
    "sales_rank", "reviews", "rating", "match_quality",
    "variations", "Product Size", "Buy Box",
    "Amazon Sells and In Stock", "ip_risk", "score",
    "Source URL", "Amazon URL", "UPC / EAN"
]
cols_available = [c for c in cols_export if c in df_safe.columns]

print(f"\n--- TOP 30 PRODUITS SAFE (sans risque IP) ---\n")
if len(df_safe) > 0:
    top30 = df_safe.head(30)
    for i, (_, row) in enumerate(top30.iterrows(), 1):
        bb = row.get("Buy Box", "?")
        amz_stock = str(row.get("Amazon Sells and In Stock", "")).replace("out of stock", "Non").replace("in stock", "OUI")
        print(f"  {i:2d}. [{row['score']:2d}pts] {row['Brand']:<20s} | {row['profit']:.2f}EUR profit | {row['roi']:.0f}% ROI | {row['monthly_sales']} ventes/mois | {row['num_sellers']} vendeurs | ASIN: {row['ASIN']}")
        print(f"      Casto: {row['price_source']:.2f}EUR -> Amz: {row['price_amazon']:.2f}EUR | Rank: {row['sales_rank']} | {row.get('Product Size','')} | BuyBox: {bb} | Amz vendeur: {amz_stock}")
        title = str(row["Title"])[:80]
        print(f"      {title}")
        print()

# Export
df_safe[cols_available].to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
print(f"\n[EXPORT] {len(df_safe)} produits SAFE exportes -> {OUTPUT_PATH}")

if len(df_iprisk) > 0:
    iprisk_path = OUTPUT_PATH.replace("_ranked.csv", "_ip_risk.csv")
    df_iprisk[cols_available].to_csv(iprisk_path, index=False, encoding="utf-8-sig")
    print(f"[EXPORT] {len(df_iprisk)} produits IP RISK exportes -> {iprisk_path}")

# Stats globales
print(f"\n{'=' * 70}")
print("RESUME GLOBAL")
print("=" * 70)
print(f"  Produits bruts charges       : {len(df) + dupes}")
print(f"  Apres deduplication          : {len(df)}")
print(f"  Produits viables             : {len(df_viable)}")
print(f"  --> SAFE (exploitables)      : {len(df_safe)}")
print(f"  --> IP RISK (a verifier)     : {len(df_iprisk)}")
if len(df_safe) > 0:
    print(f"\n  Stats produits SAFE :")
    print(f"    Profit moyen         : {df_safe['profit'].mean():.2f} EUR")
    print(f"    Profit median        : {df_safe['profit'].median():.2f} EUR")
    print(f"    ROI moyen            : {df_safe['roi'].mean():.0f}%")
    print(f"    Ventes moy/mois      : {df_safe['monthly_sales'].mean():.0f}")
    top_categories = df_safe["Amazon Category"].value_counts().head(10)
    print(f"\n  Top categories SAFE :")
    for cat, cnt in top_categories.items():
        print(f"    {cat:<30s} : {cnt} produits")
    top_brands = df_safe["Brand"].value_counts().head(10)
    print(f"\n  Top marques SAFE :")
    for brand, cnt in top_brands.items():
        print(f"    {brand:<30s} : {cnt} produits")
