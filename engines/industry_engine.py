import pandas as pd

class IndustryEngine:
    """
    🏭 產業中心 (Industry Center) - TQAI Pro 跨界生醫與前沿科技擴充版

    將 ScannerEngine 的全台股掃描結果，依產業分類聚合成「產業排名」，
    特別強化對「生物電腦」、「合成生物學」與「先進半導體」的資金流向追蹤。
    """

    # 專屬股票 → 產業分類對照表
    INDUSTRY_MAP = {
        # === 核心跨界生醫與生物電腦矩陣 ===
        # 1. 生物晶片與先進封測 (底層硬體與微流體整合)
        "2330": "生物晶片與先進封測", # 台積電 (底層製程/矽光子)
        "3374": "生物晶片與先進封測", # 精材 (晶圓級封裝/影像感測)
        "6223": "生物晶片與先進封測", # 旺矽 (探針卡/檢測)
        "3711": "生物晶片與先進封測", # 日月光投控 (先進封裝)
        
        # 2. AI 醫療與智慧生醫運算 (演算法與醫療平台)
        "6841": "AI醫療與智慧生醫",   # 長佳智能 (純度最高 AI 醫療影像)
        "2382": "AI醫療與智慧生醫",   # 廣達 (跨界生醫/雲象科技)
        "3231": "AI醫療與智慧生醫",   # 緯創 (智慧醫療設備/外骨骼)
        "2356": "AI醫療與智慧生醫",   # 英業達 (精準醫療/生醫新創)
        
        # 3. 合成生物與前沿創投 (CDMO 與早期技術孵化)
        "6472": "合成生物與前沿創投", # 保瑞 (大分子/小分子 CDMO)
        "6901": "合成生物與前沿創投", # 鑽石投資 (前沿生化創投風向球)
        "4743": "合成生物與前沿創投", # 合一 (新藥研發與前沿生技)
        "6712": "合成生物與前沿創投", # 長聖 (再生醫療/細胞治療)

        # === 大盤資金流向觀測指標 (保留傳統強勢板塊作對照) ===
        "2317": "電子代工", "2454": "半導體", "2308": "AI Server／散熱",
        "2379": "半導體", "3034": "半導體", "2412": "電信", "2881": "金融",
        "2603": "航運", "1515": "重電與綠能", "1101": "傳產水泥"
    }

    @staticmethod
    def get_industry(stock_code: str) -> str:
        code = str(stock_code).split(".")[0].strip()
        return IndustryEngine.INDUSTRY_MAP.get(code, "其他/未分類")

    @staticmethod
    def _to_stars(score: float) -> str:
        if score >= 75: return "★★★★★"
        elif score >= 65: return "★★★★☆"
        elif score >= 55: return "★★★☆☆"
        elif score >= 45: return "★★☆☆☆"
        else: return "★☆☆☆☆"

    @staticmethod
    def rank_industries(scan_result_df: pd.DataFrame) -> pd.DataFrame:
        if scan_result_df is None or scan_result_df.empty:
            return pd.DataFrame()

        df = scan_result_df.copy()
        df["產業"] = df["代碼"].apply(IndustryEngine.get_industry)

        grouped = df.groupby("產業").agg(
            平均AIScore=("AI Score", "mean"),
            成分股數=("代碼", "count"),
            強勢股數=("AI Score", lambda s: int((s >= 70).sum())),
            弱勢股數=("AI Score", lambda s: int((s <= 45).sum())),
        ).reset_index()

        grouped["強勢比例(%)"] = (grouped["強勢股數"] / grouped["成分股數"] * 100).round(1)
        grouped["平均AIScore"] = grouped["平均AIScore"].round(1)
        grouped["產業評級"] = grouped["平均AIScore"].apply(IndustryEngine._to_stars)

        grouped = grouped.sort_values("平均AIScore", ascending=False).reset_index(drop=True)
        grouped.insert(0, "排名", range(1, len(grouped) + 1))

        return grouped[["排名", "產業", "產業評級", "平均AIScore", "強勢比例(%)", "成分股數", "強勢股數", "弱勢股數"]]

    @staticmethod
    def get_industry_constituents(scan_result_df: pd.DataFrame, industry_name: str) -> pd.DataFrame:
        if scan_result_df is None or scan_result_df.empty:
            return pd.DataFrame()

        df = scan_result_df.copy()
        df["產業"] = df["代碼"].apply(IndustryEngine.get_industry)
        result = df[df["產業"] == industry_name].sort_values("AI Score", ascending=False).reset_index(drop=True)
        return result.drop(columns=["產業"])