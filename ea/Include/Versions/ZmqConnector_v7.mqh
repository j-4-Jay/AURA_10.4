//+------------------------------------------------------------------+
//|                                                ZmqConnector.mqh  |
//|                                           AURA-STRICT-PROTOCOL   |
//+------------------------------------------------------------------+
#property copyright "AURA Institutional Framework"
#property link      "https://aura-quant.com"

// We now pass the entire JSON payload that we built in the MasterEA OnTick()
bool SendTickToAURA(string json_payload)
{
   string headers;
   char post_data[], result[];
   
   // Convert string to utf-8 char array
   StringToCharArray(json_payload, post_data, 0, WHOLE_ARRAY, CP_UTF8);
   
   // [CRITICAL FIX] Strip the trailing null terminator (\0) that MT5 adds by default
   ArrayResize(post_data, ArraySize(post_data) - 1);
   
   string url = "http://127.0.0.1:8000/api/v1/mt5/tick"; 
   
   // Increased timeout to 500ms for stable localhost routing
   int res = WebRequest("POST", url, "Content-Type: application/json\r\n", 500, post_data, result, headers);
   
   if(res == 200) return true;
   else {
      Print("[AURA] Tick Delivery Failed. HTTP: ", res, " Error: ", GetLastError());
      Print("FastAPI Response: ", CharArrayToString(result)); // Print exact rejection reason if it fails
      return false;
   }
}

string PollAURAForOrders(string symbol)
{
   string headers;
   char post_data[], result[];
   string url = "http://127.0.0.1:8000/api/v1/mt5/poll/" + symbol;
   
   int res = WebRequest("GET", url, "", 500, post_data, result, headers);
   
   if(res == 200) {
      return CharArrayToString(result);
   }
   return "NONE";
}
//+------------------------------------------------------------------+