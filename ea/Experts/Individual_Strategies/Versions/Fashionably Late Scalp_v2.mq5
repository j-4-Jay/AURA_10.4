//+------------------------------------------------------------------+
//|                                       Fashionably Late Scalp.mq5  |
//|                                     AURA-STRICT-PROTOCOL Compliant|
//+------------------------------------------------------------------+
#property copyright "AURA Institutional Trading Gym"
#property version   "1.00"

// --- INCLUDES ---
// Include your local ZMQ and JSON libraries here
// #include <ZMQ.mqh> 
// #include <JAson.mqh>

// ===================================================================
// 1. GLOBAL BASELINE RISK MANAGEMENT & OPTUNA INPUTS
// ===================================================================
input double   GlobalMaxDrawdown    = 5.0;     // Max Drawdown % before Halt
input double   Optuna_MaxRiskAmount = 500.0;   // Maximum Risk Amount ($) - Optuna will optimize
input int      Optuna_EMAPeriod     = 9;       // EMA Period - Optuna will optimize
input double   Optuna_SL_Multiplier = 0.33;    // Distance Multiplier for Stop Loss (1/3 default)
input double   Optuna_TP_Multiplier = 1.0;     // Distance Multiplier for Take Profit (1.0 default)

// ZMQ Variables
int magic_number_scalp = 1001; 
double global_equity_start;

// Indicator Handles
int handle_ema;
int handle_vwap;

// ===================================================================
// 2. HELPER CALCULATIONS & SHARED INDICATORS
// ===================================================================
int OnInit() {
    global_equity_start = AccountInfoDouble(ACCOUNT_EQUITY);
    
    // Initialize Indicators (Parameters open to Optuna via variables)
    handle_ema = iMA(_Symbol, _Period, Optuna_EMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
    // Custom VWAP Handle (assuming a standard VWAP indicator is available)
    handle_vwap = iCustom(_Symbol, _Period, "VWAP"); 
    
    // Initialize ZMQ Socket here...
    return(INIT_SUCCEEDED);
}

void OnTick() {
    // 1. Calculate Baseline Risk
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double floating_pnl = AccountInfoDouble(ACCOUNT_PROFIT);
    if ((global_equity_start - current_equity) / global_equity_start * 100.0 > GlobalMaxDrawdown) {
        // CLOSE ALL TRADES AND HALT
        return; 
    }

    // 2. Grab Indicator Arrays
    double ema_array[], vwap_array[];
    CopyBuffer(handle_ema, 0, 0, 3, ema_array);
    CopyBuffer(handle_vwap, 0, 0, 3, vwap_array);

    // Calculate LOD & HOD (Low/High of the Day)
    double lod = iLow(_Symbol, PERIOD_D1, 0);
    double hod = iHigh(_Symbol, PERIOD_D1, 0);
    
    // 3. Build Observation Payload for RL Agent
    string observation_payload = BuildObservation(ema_array[0], vwap_array[0], floating_pnl);
    
    // 4. ZMQ Send & Receive
    // ZMQ_Send(observation_payload);
    // string action_payload = ZMQ_Receive(); 
    
    // 5. Route the Action
    // ParseActionAndRoute(action_payload, lod, hod, ema_array, vwap_array);
}

// ===================================================================
// 3. ISOLATED STRATEGY LOGIC MODULES (Fashionably Late Scalp)
// ===================================================================
void ExecuteFashionablyLateScalp(string action, double lot_size, double lod, double hod, double current_ema, double prev_ema, double current_vwap, double prev_vwap) {
    
    // Optuna controls the mathematical sizing; RL triggers the execution mode
    double current_price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    
    // Check Entry Conditions locally to ensure validity (Optional, but safe for Gym)
    bool is_ema_upsloping = (current_ema > prev_ema);
    bool is_vwap_flat_down = (current_vwap <= prev_vwap);
    bool is_crossing = (prev_ema < prev_vwap && current_ema > current_vwap);
    
    if (action == "BUY" && is_crossing && is_ema_upsloping && is_vwap_flat_down) {
        
        // Measured Move Calculation
        double measured_move = current_vwap - lod;
        
        // Dynamic Risk Parameters mapped from Optuna variables
        double sl_price = current_price - (measured_move * Optuna_SL_Multiplier);
        double tp_price = current_price + (measured_move * Optuna_TP_Multiplier);
        
        // Execute Trade using lot_size derived from MaxRiskAmount (Math omitted for brevity)
        // OrderSend(...)
    }
}

// ===================================================================
// 4. ZMQ NETWORKING & TICK EXECUTION
// ===================================================================
string BuildObservation(double current_ema, double current_vwap, double pnl) {
    // Construct JSON String
    return "{ \"symbol\": \"" + _Symbol + "\", \"bid\": " + DoubleToString(SymbolInfoDouble(_Symbol, SYMBOL_BID), 5) + ", \"floating_pnl\": " + DoubleToString(pnl, 2) + ", \"indicators\": { \"ema\": " + DoubleToString(current_ema, 5) + ", \"vwap\": " + DoubleToString(current_vwap, 5) + "} }";
}