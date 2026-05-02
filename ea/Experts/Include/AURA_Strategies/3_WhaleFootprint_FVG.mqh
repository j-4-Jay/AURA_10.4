//+------------------------------------------------------------------+
//|                                   3_WhaleFootprint_FVG.mqh       |
//|                               AURA Institutional Trading Gym     |
//+------------------------------------------------------------------+

string EvaluateWhaleFootprintFVG(
    double current_price,
    double fvg_top, 
    double fvg_bottom,
    double &suggested_sl, 
    double &suggested_tp
) {
    // If we have an active bullish FVG (fvg_top > fvg_bottom)
    if (fvg_bottom > 0 && fvg_top > fvg_bottom) {
        // Price taps into the FVG to mitigate
        if (current_price <= fvg_top && current_price >= fvg_bottom) {
            suggested_sl = fvg_bottom - (current_price * 0.0005); // Stop just under the FVG block
            suggested_tp = current_price + (current_price * 0.003); // Target liquidity pool above
            return "BUY";
        }
    }
    
    // Bearish FVG inverted logic would go here
    
    return "NONE";
}