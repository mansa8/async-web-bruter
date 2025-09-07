# Async Web Enumerator (Educational)

> DISCLAIMER: This project is for **educational and research purposes only**.  
> It demonstrates asynchronous web content discovery and login form testing techniques using Python.  
> Do not use this on systems or networks you do not own or explicitly control.

## Overview
This project provides an asynchronous web enumerator tool written in Python.  
It is intended for **lab environments** to practice:

- Discovering hidden directories and files on a web server  
- Parsing HTML forms to detect login mechanisms (example: Joomla)  
- Learning asynchronous web requests with `aiohttp` and `asyncio`  
- Building command-line tools for security research  

## Features
- Asynchronous requests for fast enumeration  
- Configurable headers and cookies via JSON file  
- Directory and file extension brute force (safe lab use)  
- Basic login form testing against Joomla (for educational study)  
- Logging and JSON output of discovered paths  
- Graceful interrupt handling  

## Project Structure
```
.
├── src/
│   └── content_bruter.py
├── README.md
├── requirements.txt
├── LICENSE
├── .gitignore
├── CONTRIBUTING.md
├── CHANGELOG.md
└── config.example.json
```

## Quick Start (Lab Only)
```bash
pip install -r requirements.txt

# Directory discovery (lab)
python src/content_bruter.py dir -u http://127.0.0.1/ -w wordlist.txt

# Joomla login form detection (lab)
python src/content_bruter.py joomla -u http://127.0.0.1/administrator/ -U admin -w passwords.txt
```

## Educational Value
This project demonstrates:  
- Using `asyncio` and `aiohttp` for high-performance web requests  
- Queue-based asynchronous task handling  
- Basic HTML form parsing with BeautifulSoup  
- CLI tool design with argparse  
- Logging and structured JSON output  

## Ethical Use
- Use only in controlled labs or systems you own  
- Do not use for unauthorized scanning or brute forcing  
- Educational purpose: learning asynchronous web enumeration  

## License
Licensed under GPL-3.0.

Author: Ishaq — Async Web Enumerator (Educational)

## Support My Work

If you find my projects helpful and want to support me, you can donate using the address below:

**USDT (TRC-20):** TAW81Mk7z7TTGRMMve91fgAyCGskXVvjy7
