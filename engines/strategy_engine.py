import pandas as pd
import numpy as np

class StrategyEngine:
    """
    🧠 多智能體決策引擎 (Strategy Engine) - TQAI Pro 前沿成長股特化版 v2.5.2
    """
    @staticmethod
    def generate_signals(df: pd.DataFrame):
        df = df.copy()
        if df.empty or 'atr_14' not in df.columns:
            return df
            
        c, atr = df['close'], df['atr_14']
        
        # ==========================================
        # 1. 市場狀態識別層 (Market Regime Engine)
        # ==========================================
        cond_bull_trend = (df['sma_60_slope'] > 0.4) & (c > df['sma_60'])
        cond_bear_trend = (df['sma_60_slope'] < -0.4) & (c < df['sma_60'])
        
        vol_mean = df['volatility_ratio'].rolling(60, min_periods=5).mean()
        cond_high_vol = df['volatility_ratio'] > (vol_mean * 1.3)
        
        df['market_regime'] = np.select(
            [cond_bull_trend & ~cond_high_vol, cond_bear_trend, cond_high_vol],
            ["📈 穩健多頭趨勢", "📉 弱勢空頭格局", "⚠️ 高波動震盪區"],
            default="🔄 低波盤整區"
        )

        # ==========================================
        # 2. 多智能體辯論層 (Multi-Agent Layer)
        # ==========================================
        macd_growing = df['macd_hist'] > df['macd_hist'].shift(1)
        obv_bullish = df['obv'] > df['obv_sma']
        
        bull_score = np.clip(
            35 + 
            np.where(c > df['ema_8'], 15, 0) + 
            np.where((df['macd_hist'] > 0) & macd_growing, 15, np.where(df['macd_hist'] > 0, 10, 0)) + 
            np.where((df['rvol'] > 1.3) & (c > df['sma_20']), 15, 0) +
            np.where(obv_bullish, 10, 0) +  
            np.where(c > df['sma_60'], 10, 0), 0, 100
        )
        df['bull_score'] = bull_score
        df['bull_reason'] = np.select(
            [bull_score >= 80, bull_score >= 60],
            ["強烈看多：價量齊揚，MACD動能加速擴張且OBV籌碼湧入，多方掌握絕對優勢。", 
             "偏多看待：維持在關鍵均線之上，具備基礎上漲動能與量能支撐。"],
            default="動能平庸：缺乏關鍵性突破，多方量能不足。"
        )

        bear_score = np.clip(
            40 + 
            np.where(c < df['ema_8'], 20, 0) + 
            np.where(df['rsi_14'] < 45, 20, 0) + 
            np.where(df['k_9'] < df['d_9'], 20, 0), 0, 100
        )
        df['bear_score'] = bear_score
        df['bear_reason'] = np.select(
            [bear_score >= 80, bear_score >= 60],
            ["強烈警告：短均線蓋頭，指標高檔死叉或呈現嚴重弱勢，空方掌控局勢。", 
             "潛在風險：出現部分動能衰退跡象，留意拉回風險。"],
            default="未見異常：目前無明顯做空結構破壞現象。"
        )

        bias_60 = (c - df['sma_60']) / (df['sma_60'] + 1e-9) * 100
        cond_overextended = (bias_60 > 25) | (bias_60 < -15)
        
        risk_score = np.clip(
            20 + 
            np.where(cond_overextended, 30, 0) + 
            np.where(cond_high_vol, 25, 0) + 
            np.where(c < df['sma_200'], 25, 0), 0, 100
        )
        df['risk_score'] = risk_score
        df['risk_reason'] = np.select(
            [risk_score >= 70, risk_score >= 45],
            ["🚨 系統性風險高：結構性超買/超賣，或處於年線之下，隨時有重整或重挫風險。", 
             "⚠️ 波動放大：市場情緒較為激動，高波動族群建議嚴守風險預算點位。"],
            default="✅ 風險可控：波動率與乖離率處於健康成長區，安全邊際合理。"
        )

        # ==========================================
        # 3. Judge Agent (主審裁決系統)
        # ==========================================
        raw_ai_score = (bull_score * 0.6) + ((100 - bear_score) * 0.4)
        risk_penalty = np.where(risk_score >= 75, 0.6, np.where(risk_score >= 50, 0.8, 1.0))
        df['ai_score'] = np.clip(raw_ai_score * risk_penalty, 0, 100)
        
        df['confidence'] = np.select(
            [df['ai_score'] >= 75, df['ai_score'] <= 40],
            ["High (高信心)", "Low (低信心)"],
            default="Medium (中性)"
        )
        
        df['action_guide'] = np.select(
            [df['ai_score'] >= 70, (df['ai_score'] >= 45) & (df['ai_score'] < 70), df['ai_score'] < 45],
            ["🎯 積極作多 (Agent 共識偏多，通過前沿波段風控審查)", 
             "👀 震盪觀望 (多空分歧，建議控制倉位或等待拉回低接)", 
             "✂️ 嚴格保守 (空頭論點勝出或風險過高，建議減碼防禦)"],
            default="未知狀態"
        )
        
        # ==========================================
        # 4. 動態風險預算 (ATR 進攻與防守)
        # ==========================================
        df['stop_loss'] = c - (2.0 * atr)
        df['target_1'] = c + (2.5 * atr)
        df['target_2'] = c + (5.0 * atr)
        
        return df