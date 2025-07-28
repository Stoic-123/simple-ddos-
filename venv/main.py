import asyncio
import argparse
import logging
from stress_tester import StressTester
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stress_test_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_file: str) -> dict:
    try:
        with open(config_file, 'r') as f:
            import json
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        return {}

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ethical web server stress testing tool. Use only with explicit permission."
    )
    parser.add_argument('--url', type=str, help="Target URL (HTTP/HTTPS) to test")
    parser.add_argument('--rps', type=int, default=100, help="Maximum requests per second (default: 100)")
    parser.add_argument('--duration', type=int, default=60, help="Test duration in seconds (default: 60)")
    parser.add_argument('--proxies', type=str, nargs='*', help="List of proxy URLs (e.g., http://proxy1:port)")
    parser.add_argument('--methods', type=str, nargs='*', default=['GET'], choices=['GET', 'POST'], help="HTTP methods to use (default: GET)")
    parser.add_argument('--config', type=str, help="Path to JSON config file")
    return parser.parse_args()

def validate_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.scheme in ['http', 'https'] and parsed.netloc)

async def show_progress(tester):
    import sys
    while tester.active:
        total = tester.results['total_requests']
        success = tester.results['successful_requests']
        failed = tester.results['failed_requests']
        print(f"\rRequests: {total} | Success: {success} | Failed: {failed}", end='', flush=True)
        await asyncio.sleep(1)
    print()  # Newline after done

async def main():
    args = parse_args()

    # Load config if provided, otherwise use command-line args as base
    config = load_config(args.config) if args.config else {}
    
    # Update config with command-line args, prioritizing cmd args over config
    config.update({
        'target_url': args.url if args.url else config.get('target_url'),
        'max_rps': args.rps if args.rps is not None else config.get('max_rps', 100),
        'duration': args.duration if args.duration is not None else config.get('duration', 60),
        'proxies': args.proxies if args.proxies is not None else config.get('proxies', []),
        'methods': args.methods if args.methods is not None else config.get('methods', ['GET'])
    })

    # Ensure target_url is provided either via --url or config
    if not config.get('target_url'):
        logger.error("No target URL provided. Use --url or specify 'target_url' in config.json.")
        return

    if not validate_url(config['target_url']):
        logger.error("Invalid URL. Must be HTTP or HTTPS.")
        return

    print("WARNING: This tool is for ethical stress testing only.")
    print("Misuse may violate laws or terms of service.")

    tester = StressTester(
        target_url=config['target_url'],
        max_rps=config['max_rps'],
        duration=config['duration'],
        proxies=config.get('proxies', []),
        methods=config.get('methods', ['GET']),
        config=config
    )

    # Run stress test and progress reporter concurrently
    await asyncio.gather(
        tester.run(),
        show_progress(tester)
    )
    tester.print_results()

if __name__ == "__main__":
    asyncio.run(main())