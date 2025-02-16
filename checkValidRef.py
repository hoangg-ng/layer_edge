import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor
import random

def load_proxies(proxy_file):
    with open(proxy_file, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def load_addresses(address_file):
    with open(address_file, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def get_random_proxy(proxies):
    return random.choice(proxies)

def get_referral_code(address, proxy):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
        'origin': 'https://dashboard.layeredge.io',
        'referer': 'https://dashboard.layeredge.io/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
    }
    
    try:
        url = f'https://referralapi.layeredge.io/api/referral/wallet-details/{address}'
        proxies = {
            'http': f'{proxy}',
            'https': f'{proxy}'
        }
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'referralCode' in data['data']:
                print(f"Got referral code for {address}: {data['data']['referralCode']}")
                return data['data']['referralCode']
    except Exception as e:
        print(f"Error getting referral code for {address}: {str(e)}")
    return None

def verify_referral_code(code, proxy):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
        'content-type': 'application/json',
        'origin': 'https://dashboard.layeredge.io',
        'referer': 'https://dashboard.layeredge.io/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
    }
    
    try:
        url = 'https://referralapi.layeredge.io/api/referral/verify-referral-code'
        proxies = {
            'http': f'{proxy}',
            'https': f'{proxy}'
        }
        data = {"invite_code": code}
        response = requests.post(url, headers=headers, json=data, proxies=proxies, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"Verification result for {code}: {result}")
            if 'data' in result and 'valid' in result['data']:
                return result['data']['valid']
    except Exception as e:
        print(f"Error verifying code {code}: {str(e)}")
    return False

def process_address(address, proxies):
    proxy = get_random_proxy(proxies)
    code = get_referral_code(address, proxy)
    if code:
        time.sleep(0.5)  # Giảm delay xuống 0.5s
        proxy = get_random_proxy(proxies)  
        if verify_referral_code(code, proxy):
            print(f"Valid code found: {code} from address {address}")
            with open('valid_codes.txt', 'a') as f:
                f.write(f"{code}\n")

def main():
    proxies = load_proxies('proxy.txt')
    addresses = load_addresses('address.txt')
    
    print(f"Loaded {len(proxies)} proxies and {len(addresses)} addresses")
    print("Starting with 50 threads...")
    
    # Tăng số lượng worker lên 50
    with ThreadPoolExecutor(max_workers=50) as executor:
        # Xử lý tất cả địa chỉ một lần
        futures = [executor.submit(process_address, address, proxies) for address in addresses]
        
        # Đợi tất cả công việc hoàn thành
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"Thread error: {str(e)}")

    print("All tasks completed!")

if __name__ == "__main__":
    main()