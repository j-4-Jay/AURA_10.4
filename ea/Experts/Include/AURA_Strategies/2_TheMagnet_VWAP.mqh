//+------------------------------------------------------------------+
//|                                   2_TheMagnet_VWAP.mqh           |
//|                               AURA Institutional Trading Gym     |
//+------------------------------------------------------------------+

string EvaluateTheMagnetVWAP(
    double current_price,
    double current_vwap,
    double upper_band,
    double lower_band,
    double tick_volume_current,
    double tick_volume_prev,
    double &suggested_sl, 
    double &suggested_tp
) {
    // SELL: Price tagged upper standard deviation band, volume dropping (exhaustion)
    if (current_price >= upper_band && tick_volume_current < tick_volume_prev) {
        suggested_tp = current_vwap; // Target is the mean (VWAP)
        suggested_sl = current_price + (current_price * 0.001); // Tight micro-stop above current price
        return "SELL";
    }
    
    // BUY: Price tagged lower standard deviation band, volume dropping
    if (current_price <= lower_band && tick_volume_current < tick_volume_prev) {
        suggested_tp = current_vwap;
        suggested_sl = current_price - (current_price * 0.001);
        return "BUY";
    }
    
    return "NONE";
}