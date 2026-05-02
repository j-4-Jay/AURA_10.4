//+------------------------------------------------------------------+
//|                                   5_RubberBandSnap.mqh           |
//|                               AURA Institutional Trading Gym     |
//+------------------------------------------------------------------+

string EvaluateRubberBandSnap(
    double current_price,
    double prev_price,
    double bb_upper, 
    double bb_lower,
    double bb_mid,
    double current_rsi,
    double &suggested_sl, double &suggested_tp
) {
    // Extreme Exhaustion + Pierce
    if (prev_price > bb_upper && current_price <= bb_upper && current_rsi > 80) {
        suggested_tp = bb_mid; // Snap back to the mean
        suggested_sl = prev_price + (prev_price * 0.0005); // Stop just above the piercing wick
        return "SELL";
    }
    
    if (prev_price < bb_lower && current_price >= bb_lower && current_rsi < 20) {
        suggested_tp = bb_mid; 
        suggested_sl = prev_price - (prev_price * 0.0005); // Stop just below the piercing wick
        return "BUY";
    }

    return "NONE";
}