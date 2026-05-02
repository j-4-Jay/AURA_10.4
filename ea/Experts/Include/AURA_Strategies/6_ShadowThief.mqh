//+------------------------------------------------------------------+
//|                                   6_ShadowThief.mqh              |
//|                               AURA Institutional Trading Gym     |
//+------------------------------------------------------------------+

string EvaluateShadowThief(
    double current_close,
    double current_low,
    double current_high,
    double daily_low,
    double daily_high,
    double &suggested_sl, double &suggested_tp
) {
    // Liquidity sweep of the Daily Low
    if (current_low < daily_low && current_close > daily_low) {
        double shadow_size = daily_low - current_low;
        if (shadow_size > 0) {
            suggested_sl = current_low; // Stop at the very tip of the wick
            suggested_tp = current_close + (shadow_size * 2.0); // Reward is 2x the stolen liquidity
            return "BUY";
        }
    }
    
    // Liquidity sweep of the Daily High
    if (current_high > daily_high && current_close < daily_high) {
        double shadow_size = current_high - daily_high;
        if (shadow_size > 0) {
            suggested_sl = current_high;
            suggested_tp = current_close - (shadow_size * 2.0);
            return "SELL";
        }
    }

    return "NONE";
}