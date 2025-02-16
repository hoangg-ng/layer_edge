import cloudscraper
import random
import json
import time
from typing import List, Dict, Set
import sys
import concurrent.futures
from queue import Queue
import threading
from itertools import zip_longest
from loguru import logger
from datetime import datetime

# Logging setup
logger.remove()
# logger.add(lambda msg: logger.info(msg, end=""), level="INFO")
logger.add(sys.stdout, level="TRACE",
           format="<cyan>{time:HH:mm:ss DD-MM-YYYY}</cyan> | <level>{level: <8}</level> | <level> {message} </level> ")

class ProxyManager:
    def __init__(self, proxies: List[str]):
        self.all_proxies = proxies
        self.available_proxies = Queue()
        self.active_proxies: Set[str] = set()
        self.lock = threading.Lock()
        self.reload_proxies()

    def reload_proxies(self):
        """Reload all proxies into the queue"""
        with self.lock:
            while not self.available_proxies.empty():
                self.available_proxies.get()
            random.shuffle(self.all_proxies)  # Shuffle proxies for better distribution
            for proxy in self.all_proxies:
                self.available_proxies.put(proxy)
            logger.debug(f"Reloaded {len(self.all_proxies)} proxies into the queue")

    def get_proxy(self) -> str:
        """Get a unique proxy and mark it as active"""
        with self.lock:
            if self.available_proxies.empty():
                logger.warning("Proxy pool empty, reloading proxies")
                self.reload_proxies()
            proxy = self.available_proxies.get()
            self.active_proxies.add(proxy)
            return proxy

    def release_proxy(self, proxy: str):
        """Release a proxy back to the available pool"""
        with self.lock:
            if proxy in self.active_proxies:
                self.active_proxies.remove(proxy)
                self.available_proxies.put(proxy)
                logger.debug(f"Released proxy: {proxy}")

class LayerEdgeRegistration:
    def __init__(self, max_workers: int = 10):
        self.base_url = "https://referralapi.layeredge.io/api"
        self.max_workers = max_workers
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://dashboard.layeredge.io",
            "referer": "https://dashboard.layeredge.io/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        self.success_count = 0
        self.failed_count = 0
        self.stats_lock = threading.Lock()

    def update_stats(self, success: bool):
        with self.stats_lock:
            if success:
                self.success_count += 1
            else:
                self.failed_count += 1

    def load_file(self, filename: str) -> List[str]:
        try:
            with open(filename, 'r') as file:
                lines = [line.strip() for line in file if line.strip()]
                logger.info(f"Loaded {len(lines)} entries from {filename}")
                return lines
        except FileNotFoundError:
            logger.error(f"Error: {filename} not found!")
            sys.exit(1)

    def format_proxy(self, proxy: str) -> Dict[str, str]:
        # Handle proxy format: username:password@ip:port
        if not proxy.startswith(('http://', 'https://')):
            proxy = f'http://{proxy}'
            # If proxy contains @ symbol, it has authentication
            if '@' in proxy:
                # Already in correct format for requests
                pass
            else:
                # Add authentication if missing
                auth, host = proxy.split('@')
                if ':' in auth and ':' in host:
                    proxy = f'http://{auth}@{host}'
        return {'http': proxy, 'https': proxy}

    def verify_referral(self, scraper: cloudscraper.CloudScraper, invite_code: str) -> bool:
        url = f"{self.base_url}/referral/verify-referral-code"
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
            'content-type': 'application/json',
            'origin': 'https://dashboard.layeredge.io',
            'priority': 'u=1, i',
            'referer': 'https://dashboard.layeredge.io/',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
        }
    
        try:
            response = scraper.post(url,headers=headers ,json={"invite_code": invite_code}, timeout=30)
            logger.debug(f"{response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if 'data' in result and 'valid' in result['data']:
                    logger.debug(f"Successfully verified referral code: {invite_code}, Valid: {result['data']['valid']}")
                    return result['data']['valid']
                else:
                    logger.warning(f"Invalid response format for code: {invite_code}")
            else:
                logger.warning(f"Failed to verify code {invite_code} (Status: {response.status_code})")
                
        except Exception as e:
            logger.error(f"Error verifying referral code {invite_code}: {str(e)}")
        
        return False

    def register_wallet(self, scraper: cloudscraper.CloudScraper, invite_code: str, wallet_address: str) -> bool:
        url = f"{self.base_url}/referral/register-wallet/{invite_code}"
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
            'content-type': 'application/json',
            'origin': 'https://dashboard.layeredge.io',
            'priority': 'u=1, i',
            'referer': 'https://dashboard.layeredge.io/',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
        }
        try:
            response = scraper.post(
                url, 
                headers=headers,
                json={"walletAddress": wallet_address}, 
                timeout=30
            )
            logger.debug(f"Register response: {response.text}")  # Thêm log response
            
            if response.status_code == 200:
                logger.info(f"Successfully registered wallet: {wallet_address}")
                return True
            elif response.status_code == 409:
                logger.warning(f"Wallet {wallet_address} already registered with a referral code")
                return True  # Consider as success since it's already registered
            else:
                logger.warning(f"Failed to register wallet: {wallet_address} (Status: {response.status_code})")
                return False
        except Exception as e:
            logger.error(f"Error registering wallet {wallet_address}: {str(e)}")
            return False

    def is_proxy_error(self, error: Exception) -> bool:
        """Check if the error is related to proxy issues"""
        error_str = str(error).lower()
        proxy_errors = [
            'proxyerror',
            'proxy authentication required',
            'unable to connect to proxy',
            'tunnel connection failed',
            'cannot connect to proxy',
            'connection timeout',
            'connection refused'
        ]
        return any(err in error_str for err in proxy_errors)

    def process_wallet(self, address: str, ref_codes: List[str], proxy_manager: ProxyManager) -> None:
        """Process a single wallet with unique proxy"""
        max_retries = 3
        retry_count = 0
        used_proxies = set()
        success = False

        while retry_count < max_retries and not success:
            proxy = proxy_manager.get_proxy()
            while proxy in used_proxies:
                proxy_manager.release_proxy(proxy)
                proxy = proxy_manager.get_proxy()
            
            used_proxies.add(proxy)
            try:
                formatted_proxy = self.format_proxy(proxy)
                invite_code = random.choice(ref_codes)

                scraper = cloudscraper.create_scraper()
                scraper.proxies = formatted_proxy

                if retry_count == 0:
                    logger.info(f"Processing wallet: {address}")
                else:
                    logger.info(f"Retrying wallet: {address} (Attempt {retry_count + 1})")
                
                logger.debug(f"Using proxy: {formatted_proxy['http']}")
                logger.debug(f"Using invite code: {invite_code}")

                verify_result = self.verify_referral(scraper, invite_code)

                if not verify_result:
                    logger.warning(f"Verify failed for invite code: {invite_code}")
                
                if self.register_wallet(scraper, invite_code, address):
                    success = True
                    logger.success(f"Successfully registered wallet {address}")
                    break
                else:
                    logger.error(f"Failed to register wallet {address}")

            except Exception as e:
                proxy_manager.release_proxy(proxy)
                
                if self.is_proxy_error(e):
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"Proxy error for {address}, retrying with new proxy... ({retry_count}/{max_retries})")
                        time.sleep(random.uniform(1, 2))
                        continue
                    else:
                        logger.error(f"Max retries reached for wallet {address}")
                else:
                    logger.error(f"Non-proxy error for wallet {address}: {str(e)}")
                    break

            finally:
                proxy_manager.release_proxy(proxy)
                time.sleep(random.uniform(0.5, 1.5))

        self.update_stats(success)

    def process_all_wallets(self, addresses: List[str], ref_codes: List[str], proxy_manager: ProxyManager):
        """Process all wallets using ThreadPoolExecutor"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.process_wallet, address, ref_codes, proxy_manager)
                for address in addresses if address
                ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Thread error: {str(e)}")

    def print_stats(self):
        """Print registration statistics"""
        logger.info("=== Registration Statistics ===")
        logger.info(f"Successful registrations: {self.success_count}")
        logger.info(f"Failed registrations: {self.failed_count}")
        total = self.success_count + self.failed_count
        if total > 0:
            success_rate = (self.success_count / total) * 100
            logger.info(f"Success rate: {success_rate:.2f}%")
        logger.info("===========================")

    def run(self):
        logger.info("Starting LayerEdge Registration")
        # Load data from files
        ref_codes = self.load_file('ref.txt')
        addresses = self.load_file('address.txt')
        proxies = self.load_file('proxy.txt')

        if len(proxies) < self.max_workers:
            logger.warning(f"Not enough proxies ({len(proxies)}) for {self.max_workers} workers")
            self.max_workers = len(proxies)

        # Initialize proxy manager
        proxy_manager = ProxyManager(proxies)

        start_time = time.time()
        logger.info(f"Starting registration with {self.max_workers} workers...")
        
        # Process all wallets
        self.process_all_wallets(addresses, ref_codes, proxy_manager)

        # Print final statistics
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Total execution time: {duration:.2f} seconds")
        self.print_stats()

if __name__ == "__main__":
    try:
        logger.info("Initializing LayerEdge Registration Script")
        registration = LayerEdgeRegistration(max_workers=10)
        registration.run()
    except KeyboardInterrupt:
        logger.warning("Script terminated by user")
    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")