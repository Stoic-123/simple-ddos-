import aiohttp
import asyncio
import random
import time
import logging
import ssl
import certifi
import csv
import os
import json
from typing import Dict, List, Optional
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor
import numpy as np

logger = logging.getLogger(__name__)

class StressTester:
    def __init__(
        self,
        target_url: str,
        max_rps: int,
        duration: int,
        proxies: Optional[List[str]] = None,
        methods: List[str] = None,
        config: Dict = None
    ):
        self.target_url = target_url
        self.max_rps = max_rps
        self.duration = duration
        self.proxies = proxies or []
        self.methods = methods or ['GET']
        self.config = config or {}
        self.ua = UserAgent()
        self.results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'status_codes': {},
            'rate_limit_detected': False,
            'timestamps': []
        }
        self.start_time = None
        self.active = True
        self.executor = ThreadPoolExecutor(max_workers=100)
        self.rate_limit_backoff = 0
        self.proxy_pool = self.proxies.copy()

    async def validate_proxy(self, proxy: str, session: aiohttp.ClientSession) -> bool:
        try:
            async with session.get('https://httpbin.org/ip', proxy=proxy, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            logger.warning(f"Proxy {proxy} is invalid.")
            return False

    async def initialize_proxies(self, session: aiohttp.ClientSession):
        valid_proxies = []
        for proxy in self.proxies:
            if await self.validate_proxy(proxy, session):
                valid_proxies.append(proxy)
        self.proxy_pool = valid_proxies or [None]
        logger.info(f"Initialized {len(self.proxy_pool)} valid proxies.")

    async def make_request(self, session: aiohttp.ClientSession):
        headers = {
            'User-Agent': self.ua.random,
            'Accept': random.choice(['text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'application/json', 'text/plain,*/*']),
            'Accept-Language': random.choice(['en-US,en;q=0.9', 'fr-FR,fr;q=0.8', 'es-ES,es;q=0.7']),
            'Referer': random.choice([self.target_url, 'https://www.google.com', 'https://bing.com']),
            'Cookie': f'session_id={random.randint(1000, 9999999)}'
        }
        proxy = random.choice(self.proxy_pool) if self.proxy_pool else None
        method = random.choice(self.methods)
        payload = {'data': ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=random.randint(50, 200)))} if method == 'POST' else None
        start_time = time.time()
        try:
            async with session.request(method=method, url=self.target_url, headers=headers, data=payload, proxy=proxy, timeout=10) as response:
                status = response.status
                self.results['status_codes'][status] = self.results['status_codes'].get(status, 0) + 1
                self.results['timestamps'].append(time.time())
                if status == 200:
                    self.results['successful_requests'] += 1
                    self.results['response_times'].append(time.time() - start_time)
                elif status == 429:
                    self.results['rate_limit_detected'] = True
                    self.rate_limit_backoff = min(self.rate_limit_backoff + 1, 5)
                    logger.warning(f"Rate limit detected (HTTP 429). Backing off for {self.rate_limit_backoff}s.")
                    await asyncio.sleep(self.rate_limit_backoff)
                elif status in (403, 503):
                    logger.warning(f"Server responded with HTTP {status}. Possible protection mechanism.")
                    self.results['failed_requests'] += 1
                else:
                    self.results['failed_requests'] += 1
                self.results['total_requests'] += 1
        except Exception as e:
            logger.error(f"Request failed: {e}")
            self.results['failed_requests'] += 1
            self.results['total_requests'] += 1
            if proxy and proxy in self.proxy_pool:
                self.proxy_pool.remove(proxy)
                logger.info(f"Removed unreliable proxy: {proxy}")

    async def worker(self, session: aiohttp.ClientSession, worker_id: int):
        interval = 1.0 / self.max_rps
        while self.active and (time.time() - self.start_time < self.duration):
            current_time = time.time() - self.start_time
            avg_response_time = sum(self.results['response_times'][-100:]) / len(self.results['response_times'][-100:]) if self.results['response_times'] else 1.0
            current_rps = min(self.max_rps, self.max_rps * (1.0 / max(1.0, avg_response_time * 2)))
            if current_time < self.duration * 0.2:
                current_rps *= current_time / (self.duration * 0.2)
            elif current_time > self.duration * 0.8:
                current_rps *= (self.duration - current_time) / (self.duration * 0.2)
            interval = 1.0 / max(1, current_rps)
            await self.make_request(session)
            await asyncio.sleep(interval)

    async def run(self):
        logger.info(f"Starting stress test on {self.target_url} for {self.duration} seconds at {time.strftime('%I:%M %p +07, %B %d, %Y')}")
        logger.info("Ensure you have explicit permission to test this server.")
        self.start_time = time.time()

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        conn = aiohttp.TCPConnector(ssl=ssl_context, limit=2000)
        async with aiohttp.ClientSession(connector=conn) as session:
            await self.initialize_proxies(session)
            tasks = [self.worker(session, i) for i in range(min(self.max_rps, 1000))]
            await asyncio.gather(*tasks)
        self.active = False
        self.executor.shutdown(wait=True)

    def export_results_to_csv(self):
        filename = f"stress_test_results_{int(time.time())}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Response Time (s)', 'Status Code'])
            for ts, rt in zip(self.results['timestamps'], self.results['response_times'] + [0] * (self.results['total_requests'] - len(self.results['response_times']))):
                writer.writerow([ts, rt, 200 if rt > 0 else 0])
        logger.info(f"Results exported to {filename}")

    def print_results(self):
        response_times = self.results['response_times']
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        success_rate = (self.results['successful_requests'] / self.results['total_requests'] * 100) if self.results['total_requests'] > 0 else 0
        throughput = self.results['total_requests'] / self.duration if self.duration > 0 else 0
        percentiles = np.percentile(response_times, [50, 90, 99]) if response_times else [0, 0, 0]

        logger.info("\n=== Stress Test Results ===")
        logger.info(f"Total Requests: {self.results['total_requests']}")
        logger.info(f"Successful Requests: {self.results['successful_requests']}")
        logger.info(f"Failed Requests: {self.results['failed_requests']}")
        logger.info(f"Success Rate: {success_rate:.2f}%")
        logger.info(f"Average Response Time: {avg_response_time:.3f} seconds")
        logger.info(f"Response Time Percentiles (p50, p90, p99): {percentiles[0]:.3f}, {percentiles[1]:.3f}, {percentiles[2]:.3f} seconds")
        logger.info(f"Throughput: {throughput:.2f} requests/second")
        logger.info(f"HTTP Status Codes: {self.results['status_codes']}")
        if self.results['rate_limit_detected']:
            logger.warning("Rate limiting detected during the test. Adjust RPS or consult server admin.")
        logger.info(f"Test Duration: {self.duration} seconds")
        self.export_results_to_csv()

        # Generate chart for response times
        if self.results['response_times']:
            logger.info("\nGenerating response time distribution chart...")
            chart_data = {
                "type": "line",
                "data": {
                    "labels": [str(i) for i in range(len(self.results['response_times']))],
                    "datasets": [{
                        "label": "Response Time (s)",
                        "data": [float(rt) for rt in self.results['response_times']],
                        "borderColor": "#4CAF50",
                        "backgroundColor": "rgba(76, 175, 80, 0.2)",
                        "fill": True,
                        "tension": 0.4
                    }]
                },
                "options": {
                    "scales": {
                        "x": {"title": {"display": True, "text": "Request Number"}},
                        "y": {"title": {"display": True, "text": "Response Time (s)"}, "beginAtZero": True}
                    },
                    "plugins": {
                        "title": {"display": True, "text": "Response Time Distribution"}
                    }
                }
            }
            chart_json = json.dumps(chart_data, indent=4)
            with open("chart_config.json", "w") as f:
                f.write(chart_json)
            logger.info("Chart configuration saved to chart_config.json. Copy the content into chart.html's <script> section or use the file directly.")