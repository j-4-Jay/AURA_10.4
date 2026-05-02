//+------------------------------------------------------------------+
//|                                   1_FashionablyLateScalp.mqh     |
//|                               AURA Institutional Trading Gym     |
//|                                     [AURA-STRICT-PROTOCOL]       |
//+------------------------------------------------------------------+

// This is a Strategy Cartridge. It holds NO global logic, NO ZMQ, 
// and NO global risk checks. It only takes numbers from the Master EA,
// does the math, and returns a Signal ("BUY", "SELL", "NONE").

string EvaluateFashionablyLateScalp(
    double current_ema, 
    double prev_ema, 
    double current_vwap, 
    double prev_vwap, 
    double current_price, 
    double lod, 
    double hod, 
    double &suggested_sl, 
    double &suggested_tp, 
    double sl_multiplier, 
    double tp_multiplier
) {
    
    // 1. BUY CONDITIONS (The Runner Jumps the Fence)
    bool is_ema_upsloping = (current_ema > prev_ema);
    bool is_vwap_flat_down = (current_vwap <= prev_vwap);
    bool is_crossing_up = (prev_ema < prev_vwap && current_ema > current_vwap);
    
    if (is_crossing_up && is_ema_upsloping && is_vwap_flat_down) {
        // Find Measured Move (from Low of Day to the VWAP jump)
        double measured_move = current_vwap - lod;
        
        // Anti-Chop Safety: Only trade if there was an actual move to measure
        if (measured_move > 0) {
            suggested_sl = current_price - (measured_move * sl_multiplier);
            suggested_tp = current_price + (measured_move * tp_multiplier);
            return "BUY";
        }
    }
    
    // 2. SELL CONDITIONS (Inverted logic for Short Scalps)
    bool is_ema_downsloping = (current_ema < prev_ema);
    bool is_vwap_flat_up = (current_vwap >= prev_vwap);
    bool is_crossing_down = (prev_ema > prev_vwap && current_ema < current_vwap);
    
    if (is_crossing_down && is_ema_downsloping && is_vwap_flat_up) {
        // Find Measured Move (from High of Day to the VWAP jump)
        double measured_move = hod - current_vwap;
        
        // Anti-Chop Safety
        if (measured_move > 0) {
            suggested_sl = current_price + (measured_move * sl_multiplier);
            suggested_tp = current_price - (measured_move * tp_multiplier);
            return "SELL";
        }
    }
    
    // 3. DEFAULT
    return "NONE";
}
