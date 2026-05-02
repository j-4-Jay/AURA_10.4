//+------------------------------------------------------------------+
//|                                   7_SparkPlug.mqh                |
//|                               AURA Institutional Trading Gym     |
//+------------------------------------------------------------------+

string EvaluateSparkPlug(
    double current_price,
    double prev_tick_volume,
    double avg_tick_volume,
    double prev_close,
    double prev_open,
    double prev_high,
    double prev_low,
    double &suggested_sl, double &suggested_tp
) {
    // Identify the explosion: 3x average volume and a solid body candle
    if (prev_tick_volume > (avg_tick_volume * 3.0)) {
        
        bool is_bullish_spark = (prev_close > prev_open) && (prev_close >= prev_high * 0.95); // Closes near high
        bool is_bearish_spark = (prev_close < prev_open) && (prev_close <= prev_low * 1.05); // Closes near low
        
        if (is_bullish_spark && current_price > prev_high) {
            suggested_sl = prev_low; 
            suggested_tp = current_price + (current_price * 0.002); // Fixed micro-run target
            return "BUY";
        }
        
        if (is_bearish_spark && current_price < prev_low) {
            suggested_sl = prev_high;
            suggested_tp = current_price - (current_price * 0.002);
            return "SELL";
        }
    }

    return "NONE";
}