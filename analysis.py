"""
Bristol Crime Analysis
Analyses street-level crime data for Bristol from data.police.uk
(Open Government Licence v3.0) using pandas and matplotlib.

How to use:
  1. Download the CSV files from https://data.police.uk/data/ (see README.md)
  2. Put the CSV files inside the "data" folder
  3. Run:  python analysis.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Police.uk uses these labels for types of place, not one specific street,
# so they are left out of the "top locations" chart.
GENERIC_LOCATIONS = {
    "no location","ferry terminal", "parking area", "supermarket", "shopping area",
    "petrol station", "sports/recreation area", "nightclub",
    "bus/coach station", "further/higher educational building",
    "hospital", "conference/exhibition centre", "theatre/concert hall",
}

DATA_DIR = Path("data")
OUT_DIR = Path("charts")
OUT_DIR.mkdir(exist_ok=True)


def load_data() -> pd.DataFrame:
    """Read every CSV file in the data folder into one table."""
    files = sorted(DATA_DIR.rglob("*street.csv"))
    if not files:
        raise SystemExit("No street.csv files found in the data folder. See README.md.")
    frames = [pd.read_csv(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    print(f"Loaded {len(files)} files, {len(df):,} rows")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Tidy column names, fix dates, keep Bristol only, remove bad rows."""
    df = df.copy()
    df.columns = df.columns.str.strip()

    # Keep only rows that have the fields we need
    df = df.dropna(subset=["Month", "Crime type"])

    # Month looks like "2026-01" -> real date
    df["Month"] = pd.to_datetime(df["Month"], format="%Y-%m")

    # Keep Bristol only (LSOA names start with the council area, e.g. "Bristol 012A")
    if "LSOA name" in df.columns:
        before = len(df)
        df = df[df["LSOA name"].str.contains("Bristol", na=False)]
        print(f"Kept {len(df):,} Bristol rows out of {before:,}")

    # "On or near High Street" -> "High Street"
    df["Location"] = (
        df["Location"].fillna("No Location").str.replace("On or near ", "", regex=False).str.strip()
    )

    # Remove duplicate crimes (same crime ID reported twice)
    if "Crime ID" in df.columns:
        has_id = df["Crime ID"].notna()
        df = pd.concat([df[has_id].drop_duplicates(subset="Crime ID"), df[~has_id]])

    return df.reset_index(drop=True)


def save_bar(series: pd.Series, title: str, filename: str, xlabel: str) -> None:
    """Save a horizontal bar chart."""
    ax = series.sort_values().plot(kind="barh", figsize=(9, 5), color="#2F5BEA")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(OUT_DIR / filename, dpi=150)
    plt.close()


def main() -> None:
    df = clean_data(load_data())

    # 1. Crimes by type
    by_type = df["Crime type"].value_counts()
    save_bar(by_type, "Crimes in Bristol by type", "1_crime_types.png", "Number of crimes")

    # 2. Crimes per month
    monthly = df.groupby("Month").size()
    ax = monthly.plot(figsize=(9, 4), marker="o", color="#2F5BEA")
    ax.set_title("Crimes in Bristol per month")
    ax.set_xlabel("")
    ax.set_ylabel("Number of crimes")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "2_monthly_trend.png", dpi=150)
    plt.close()

    # 3. Top 10 locations (ignoring rows with no location)
    places = df[~df["Location"].str.lower().isin(GENERIC_LOCATIONS)]["Location"].value_counts().head(10)
    save_bar(places, "Top 10 locations for crime in Bristol", "3_top_locations.png", "Number of crimes")

    # 4. What happened after the crime (outcomes)
    if "Last outcome category" in df.columns:
        outcomes = df["Last outcome category"].fillna("No outcome recorded").value_counts().head(8)
        save_bar(outcomes, "Most common outcomes", "4_outcomes.png", "Number of crimes")

    # Summary to put in the README
    print("\n--- Key findings ---")
    print(f"Total crimes: {len(df):,}")
    print(f"Most common crime type: {by_type.index[0]} ({by_type.iloc[0] / len(df):.0%} of all crimes)")
    print(f"Busiest month: {monthly.idxmax():%B %Y} ({monthly.max():,} crimes)")
    print(f"Quietest month: {monthly.idxmin():%B %Y} ({monthly.min():,} crimes)")
    print(f"Top location: {places.index[0]} ({places.iloc[0]:,} crimes)")
    print(f"\nCharts saved in the '{OUT_DIR}' folder")


if __name__ == "__main__":
    main()
