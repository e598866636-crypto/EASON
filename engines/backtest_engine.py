import pandas as pd

class BacktestEngine:
    @staticmethod
    def run_backtest(df: pd.DataFrame, initial_capital=100000):
        df = df.copy().sort_values('date').reset_index(drop=True)
        
        capital = initial_capital
        position = 0
        holding = False
        buy_price = 0
        trades = []
        equity_curve = []
        
        for i in range(len(df)):
            current_date = df.loc[i, 'date']
            # 防止 yfinance MultiIndex 造成的 Series 錯誤
            current_close = float(df.loc[i, 'close'].iloc[0] if isinstance(df.loc[i, 'close'], pd.Series) else df.loc[i, 'close'])
            
            # 使用全新的 Judge Agent AI 評分
            score = df.loc[i, 'ai_score']
            
            # AI 決策邏輯：>= 70 啟動買進， <= 45 停損/停利
            if score >= 70 and not holding:
                position = capital / current_close
                buy_price = current_close
                holding = True
                capital = 0
                trades.append({'type': 'Buy', 'date': current_date, 'price': current_close})
                
            elif score <= 45 and holding:
                capital = position * current_close
                position = 0
                holding = False
                pnl = (current_close - buy_price) / buy_price
                trades.append({'type': 'Sell', 'date': current_date, 'price': current_close, 'pnl': pnl})
            
            current_equity = capital + (position * current_close)
            equity_curve.append(current_equity)
            
        df['equity'] = equity_curve
        
        total_return = (equity_curve[-1] - initial_capital) / initial_capital * 100
        equity_series = pd.Series(equity_curve)
        roll_max = equity_series.cummax()
        drawdown = (equity_series - roll_max) / roll_max
        max_drawdown = drawdown.min() * 100
        
        sell_trades = [t for t in trades if t['type'] == 'Sell']
        win_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
        win_rate = (len(win_trades) / len(sell_trades) * 100) if len(sell_trades) > 0 else 0.0
        
        summary = {
            'initial_capital': initial_capital,
            'final_equity': equity_curve[-1],
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'total_trades': len(sell_trades),
            'win_rate': win_rate
        }
        
        return df, summary