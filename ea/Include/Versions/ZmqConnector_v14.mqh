//+------------------------------------------------------------------+
//|                                                ZmqConnector.mqh  |
//|                                           AURA-STRICT-PROTOCOL   |
//+------------------------------------------------------------------+
#property copyright "AURA Institutional Framework"
#property link      "https://aura-quant.com"

// We use blazing-fast WebRequests bound to localhost. 
// MT5 must have WebRequest allowed for http://127.0.0.1:8000 in Tools > Options > Expert Advisors

// Send the Radar/State JSON Payload to Python
bool SendTickToAURA(string json_payload)
{
   string headers;
   char post_data[], result[];
   
   StringToCharArray(json_payload, post_data, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(post_data, ArraySize(post_data) - 1);
   
   // We are using the endpoint that broadcasts to the WebSockets/Dashboard
   string url = "http://127.0.0.1:8000/api/v1/mt5/tick"; 
   
   int res = WebRequest("POST", url, "Content-Type: application/json\r\n", 200, post_data, result, headers);
   
   if(res == 200) return true;
   return false;
}

// Poll the Python Brain for the Neural Network's Orders
string PollAURAForOrders(string symbol)
{
   string headers;
   char post_data[], result[];
   
   // The Brain sends orders here, MT5 fetches them
   string url = "http://127.0.0.1:8000/api/v1/mt5/poll/" + symbol;
   
   int res = WebRequest("GET", url, "", 200, post_data, result, headers);
   
   if(res == 200) {
      string command = CharArrayToString(result);
      if(StringLen(command) > 0 && command != "NONE") {
         return command;
      }
   }
   return "NONE";
}
//+------------------------------------------------------------------+