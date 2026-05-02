 
import ollama
import time
import re

# [AURA-STRICT-PROTOCOL] Phase 2 Module 4 - The Sixth Sense
class SentimentOllamaAgent:
    def __init__(self, model_name="llama3"):
        self.model_name = model_name
        self.system_prompt = (
            "You are an institutional quantitative trading AI. "
            "Analyze the following financial headline and determine its sentiment for the asset. "
            "Reply ONLY with a single floating-point number between -1.0 (extremely bearish) and 1.0 (extremely bullish). "
            "0.0 means neutral. Do not provide any explanation or text."
        )
        print(f"[OLLAMA AGENT] Initializing Sixth Sense using model: {model_name}")

    def analyze_headline(self, headline: str) -> float:
        """
        Sends the headline to local Ollama LLM and extracts the float sentiment score.
        """
        try:
            response = ollama.chat(model=self.model_name, messages=[
                {
                    'role': 'system',
                    'content': self.system_prompt
                },
                {
                    'role': 'user',
                    'content': f"Headline: {headline}"
                }
            ])
            
            raw_output = response['message']['content'].strip()
            
            # Regex to extract the first float found in the response
            match = re.search(r'-?\d+\.\d+', raw_output)
            if match:
                score = float(match.group())
                # Clamp between -1.0 and 1.0
                return max(-1.0, min(1.0, score))
            else:
                # If LLM hallucinates and gives integer or weird format
                try:
                    return float(raw_output)
                except ValueError:
                    return 0.0 # Default to neutral on parse failure

        except Exception as e:
            print(f"[!] Ollama Inference Error: {e}")
            return 0.0

# --- VERIFICATION TEST ---
if __name__ == "__main__":
    # Ensure you have 'llama3' pulled via Ollama before running this
    agent = SentimentOllamaAgent(model_name="llama3")
    
    test_headlines = [
        "Federal Reserve unexpectedly hikes interest rates by 50 basis points, citing persistent inflation.",
        "Apple reports record Q3 earnings, shattering Wall Street estimates on iPhone sales.",
        "Standard day in the markets, SPY trades sideways with low volume.",
        "Massive crypto exchange gets hacked for $500M, CEO steps down."
    ]
    
    print("\n[AURA] Testing The Sixth Sense (Alternative Data Agent)...")
    
    total_time = 0
    for hl in test_headlines:
        start = time.time()
        score = agent.analyze_headline(hl)
        elapsed = time.time() - start
        total_time += elapsed
        
        # Color coding the output based on sentiment
        if score > 0.3:
            sentiment = "BULLISH"
        elif score < -0.3:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"
            
        print(f"-> Headline: '{hl[:50]}...'")
        print(f"   [+] Score: {score:>5.2f} [{sentiment}] | Inference Time: {elapsed:.2f}s")
        
    print(f"\n[AURA] Sentiment Test Complete. Avg Time per Inference: {(total_time/len(test_headlines)):.2f}s")
    print("[AURA-STRICT-PROTOCOL] Verify output precision to Lock Module 4.")