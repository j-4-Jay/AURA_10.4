//+------------------------------------------------------------------+
//|                                   4_TheCoil_Squeeze.mqh          |
//|                               AURA Institutional Trading Gym     |
//+------------------------------------------------------------------+

string EvaluateTheCoilSqueeze(
    double current_price,
    double bb_upper, double bb_lower,
    double kc_upper, double kc_lower,
    double ema_current, double ema_prev,
    double &suggested_sl, double &suggested_tp
) {
    bool is_squeezed = (bb_upper < kc_upper) && (bb_lower > kc_lower);
    bool price_breaking_up = (current_price > bb_upper);
    bool price_breaking_down = (current_price < bb_lower);
    
    // Momentum confirmation using EMA
    bool ema_upsloping = ema_current > ema_prev;
    bool ema_downsloping = ema_current < ema_prev;

    // Expansion breakout
    if (!is_squeezed && price_breaking_up && ema_upsloping) {
        suggested_sl = ema_current; // SL trails the EMA
        suggested_tp = current_price + (current_price * 0.005); // Fixed expansion target
        return "BUY";
    }
    
    if (!is_squeezed && price_breaking_down && ema_downsloping) {
        suggested_sl = ema_current;
        suggested_tp = current_price - (current_price * 0.005);
        return "SELL";
    }

    return "NONE";
}