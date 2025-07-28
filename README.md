
## Setup Instructions

### 1. Clone the repository

```sh
git clone https://github.com/Stoic-123/simple-ddos-kh.git
cd your-repo-name
```

### 2. Create and activate a virtual environment (recommended)

```sh
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

Make sure `requirement.txt` is in the root directory (next to `main.py`).

```sh
pip install -r requirement.txt
```

If you don't have a `requirement.txt`, install these manually:

```sh
pip install aiohttp aiohttp-socks fake-useragent certifi numpy
```

---

## Configuration

**Edit `config.json` and set your target URL and options:**

```json
{
  "target_url": "https://www.example.com/",
  "max_rps": 50,
  "duration": 60,
  "proxies": [], // put ur proxy or not put it 
  "methods": ["GET"]
}
```

- Change `"target_url"` to the website you want to test.
- Adjust `max_rps`, `duration`, `proxies`, and `methods` as needed.

---

## How to Run

### Using the config file

```sh
python main.py --config config.json
```

### Or with command-line arguments

```sh
python main.py --url https://your-target.com --rps 100 --duration 60 --methods GET POST
```

- Command-line arguments override values in `config.json`.

---

## Output

- **Real-time progress** is shown in the terminal:  
  `Requests: <total> | Success: <success> | Failed: <failed>`
- **Results** are saved to a CSV file (e.g., `stress_test_results_XXXXXXXX.csv`).
- **Chart configuration** for response times is saved to `chart_config.json`.
- **Logs** are written to `stress_test_audit.log`.

---

## Notes

- **Change the `target_url` in `config.json` before running the test.**
- Only use this tool on servers you own or have explicit permission to test.
- For SOCKS proxies, ensure you have `aiohttp-socks` installed.
- Logs and CSV results are stored in the root
