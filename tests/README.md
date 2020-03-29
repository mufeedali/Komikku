## Test inside a virtual environment

1. Create venv
```
python3 -m venv .venv
```

2. Activate venv
```
source .venv/bin/activate
```

3. Install dependencies
```
pip install --upgrade pip setuptools wheel
pip install PyGObject --no-use-pep517
pip install requests
pip install cloudscraper
pip install lxml
pip install beautifulsoup4
pip install dateparser
pip install python-magic
pip install pillow
pip install pure-protobuf
pip install unidecode
pip install pytest
pip install pytest-steps
```

## Run tests

```
python -m pytest -v
```
