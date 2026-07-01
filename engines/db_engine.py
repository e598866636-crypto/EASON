import os
import sqlite3
from datetime import datetime, timedelta

import pandas as pd


class DatabaseEngine:
    """
    🗄️ Database 資料庫中心 (SQLite)

    避免每次都重新呼叫 yfinance 下載歷史資料：
      - 第一次查詢某檔股票時，下載完整歷史並寫入 SQLite
      - 之後在「新鮮期限」內再次查詢，直接從本地資料庫讀取，速度更快、也減少對 yfinance 的請求量
      - 過了新鮮期限（預設 6 小時）才會重新向 yfinance 抓取最新資料並覆寫快取

    資料庫檔案預設位置：<專案根目錄>/data/tqai.db
    """

    DEFAULT_DB_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tqai.db"
    )

    # ==========================================
    # 連線與資料表初始化
    # ==========================================
    @staticmethod
    def get_connection(db_path: str = None):
        db_path = db_path or DatabaseEngine.DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        DatabaseEngine._init_schema(conn)
        return conn

    @staticmethod
    def _init_schema(conn):
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (ticker, date)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                ticker TEXT PRIMARY KEY,
                resolved_symbol TEXT,
                last_updated TEXT,
                row_count INTEGER
            )
        """)
        conn.commit()

    # ==========================================
    # 寫入快取
    # ==========================================
    @staticmethod
    def save_prices(ticker: str, df: pd.DataFrame, resolved_symbol: str = None, db_path: str = None):
        if df is None or df.empty:
            return

        conn = DatabaseEngine.get_connection(db_path)
        try:
            save_df = df[["date", "open", "high", "low", "close", "volume"]].copy()
            save_df["date"] = pd.to_datetime(save_df["date"]).dt.strftime("%Y-%m-%d")
            save_df.insert(0, "ticker", str(ticker))

            save_df.to_sql("stock_prices_staging", conn, if_exists="replace", index=False)

            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO stock_prices (ticker, date, open, high, low, close, volume)
                SELECT ticker, date, open, high, low, close, volume FROM stock_prices_staging
            """)
            cur.execute("DROP TABLE stock_prices_staging")
            cur.execute("""
                INSERT OR REPLACE INTO sync_metadata (ticker, resolved_symbol, last_updated, row_count)
                VALUES (?, ?, ?, ?)
            """, (str(ticker), resolved_symbol, datetime.now().isoformat(), len(save_df)))
            conn.commit()
        finally:
            conn.close()

    # ==========================================
    # 讀取快取
    # ==========================================
    @staticmethod
    def load_prices(ticker: str, db_path: str = None) -> pd.DataFrame:
        conn = DatabaseEngine.get_connection(db_path)
        try:
            df = pd.read_sql_query(
                "SELECT date, open, high, low, close, volume FROM stock_prices "
                "WHERE ticker = ? ORDER BY date",
                conn, params=(str(ticker),)
            )
        except Exception:
            df = pd.DataFrame()
        finally:
            conn.close()

        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df

    @staticmethod
    def get_resolved_symbol(ticker: str, db_path: str = None):
        conn = DatabaseEngine.get_connection(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT resolved_symbol FROM sync_metadata WHERE ticker = ?", (str(ticker),))
            row = cur.fetchone()
        finally:
            conn.close()
        return row[0] if row else None

    @staticmethod
    def get_last_updated(ticker: str, db_path: str = None):
        conn = DatabaseEngine.get_connection(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT last_updated FROM sync_metadata WHERE ticker = ?", (str(ticker),))
            row = cur.fetchone()
        finally:
            conn.close()

        if not row or not row[0]:
            return None
        try:
            return datetime.fromisoformat(row[0])
        except Exception:
            return None

    @staticmethod
    def is_fresh(ticker: str, max_age_hours: float = 6, db_path: str = None) -> bool:
        last_updated = DatabaseEngine.get_last_updated(ticker, db_path)
        if last_updated is None:
            return False
        return (datetime.now() - last_updated) < timedelta(hours=max_age_hours)

    # ==========================================
    # 工具方法：清除單一股票快取 / 查詢資料庫狀態
    # ==========================================
    @staticmethod
    def clear_cache(ticker: str, db_path: str = None):
        conn = DatabaseEngine.get_connection(db_path)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM stock_prices WHERE ticker = ?", (str(ticker),))
            cur.execute("DELETE FROM sync_metadata WHERE ticker = ?", (str(ticker),))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_db_stats(db_path: str = None) -> dict:
        conn = DatabaseEngine.get_connection(db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(DISTINCT ticker) FROM stock_prices")
            ticker_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM stock_prices")
            row_count = cur.fetchone()[0]
        finally:
            conn.close()
        return {"cached_tickers": ticker_count, "total_rows": row_count}