import pandas as pd

NON_SPENDING = {"income", "transfer"}


def to_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["date", "description", "amount", "category", "spend"])
    df["date"] = pd.to_datetime(df["date"])
    df["spend"] = df["amount"].where(~df["category"].isin(NON_SPENDING) & (df["amount"] < 0), 0.0).abs()
    return df


def summary(df: pd.DataFrame) -> dict:
    spending = df[df["spend"] > 0]
    income = df[(df["category"] == "income") & (df["amount"] > 0)]["amount"].sum()
    return {
        "total_spent": float(spending["spend"].sum()),
        "largest_purchase": float(spending["spend"].max()) if len(spending) else 0.0,
        "transaction_count": int(len(df)),
        "average_transaction": float(spending["spend"].mean()) if len(spending) else 0.0,
        "start": df["date"].min() if len(df) else None,
        "end": df["date"].max() if len(df) else None,
    }


def by_category(df: pd.DataFrame) -> pd.DataFrame:
    df_abs = df.copy()
    df_abs["abs_amount"] = df_abs["amount"].abs()
    grouped = df_abs.groupby("category")["abs_amount"].agg(["sum", "count"]).reset_index()
    grouped.columns = ["category", "total", "count"]
    total = grouped["total"].sum()
    grouped["share"] = grouped["total"] / total if total else 0.0
    return grouped.sort_values("total", ascending=False).reset_index(drop=True)


def top_merchants(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    spending = df[df["spend"] > 0].copy()
    spending["merchant"] = spending["description"].str.slice(0, 30)
    grouped = spending.groupby("merchant")["spend"].agg(["sum", "count"]).reset_index()
    grouped.columns = ["merchant", "total", "count"]
    return grouped.sort_values("total", ascending=False).head(n).reset_index(drop=True)


def daily_spend(df: pd.DataFrame) -> pd.Series:
    spending = df[df["spend"] > 0]
    if spending.empty:
        return pd.Series(dtype=float)
    return spending.groupby(spending["date"].dt.date)["spend"].sum()
