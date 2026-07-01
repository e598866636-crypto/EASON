import pandas as pd
import numpy as np

class StructureEngine:
    """
    📐 市場結構引擎 - TQAI Pro 高階版
    修正原版 ZigZag 演算法在單邊趨勢中會產生的「連續標記漂移」問題。
    採用標準的 Peak/Trough 探索機制：在同方向動能中動態更新極值，在反向偏離時確立轉折。
    """
    @staticmethod
    def add_swing_points(df: pd.DataFrame, deviation: float = 0.04):
        df = df.copy()
        if len(df) < 3:
            df['zigzag'] = np.nan
            df['zigzag_ffill'] = df['close'].ffill()
            return df
            
        c = df['close']
        pivots_idx = [0]
        pivots_val = [c.iloc[0]]
        
        # 追蹤當前尋找狀態： 0 = 初始判定, 1 = 尋找波段最高點, -1 = 尋找波段最低點
        state = 0 
        
        for i in range(1, len(df)):
            current_price = c.iloc[i]
            last_pivot_val = pivots_val[-1]
            dev = (current_price - last_pivot_val) / (last_pivot_val + 1e-9)
            
            if state == 0:
                # 初始階段：看哪邊先突破偏離度
                if dev > deviation:
                    state = 1  # 確立向上，開始尋找最高點
                    pivots_idx.append(i)
                    pivots_val.append(current_price)
                elif dev < -deviation:
                    state = -1 # 確立向下，開始尋找最低點
                    pivots_idx.append(i)
                    pivots_val.append(current_price)
                    
            elif state == 1:
                # 尋找波段高點中：
                if current_price > last_pivot_val:
                    # 價格更高，動態「更新」當前高點的位置與數值
                    pivots_idx[-1] = i
                    pivots_val[-1] = current_price
                elif dev < -deviation:
                    # 從最高點回檔超過設定值，轉折確立！確認高點，並轉向尋找低點
                    state = -1
                    pivots_idx.append(i)
                    pivots_val.append(current_price)
                    
            elif state == -1:
                # 尋找波段低點中：
                if current_price < last_pivot_val:
                    # 價格更低，動態「更新」當前低點的位置與數值
                    pivots_idx[-1] = i
                    pivots_val[-1] = current_price
                elif dev > deviation:
                    # 從最低點反彈超過設定值，轉折確立！確認低點，並轉向尋找高點
                    state = 1
                    pivots_idx.append(i)
                    pivots_val.append(current_price)
                    
        # 強制將最後一個交易日納入，確保即時資料有基底做 ffill 比較
        if pivots_idx[-1] != len(df) - 1:
            pivots_idx.append(len(df) - 1)
            pivots_val.append(c.iloc[-1])
            
        df['zigzag'] = np.nan
        # 使用 iloc 绝对位置賦值，徹底根除 Index 錯位或 SettingWithCopy 警告
        df.iloc[pivots_idx, df.columns.get_loc('zigzag')] = pivots_val
        df['zigzag_ffill'] = df['zigzag'].ffill()
        
        return df