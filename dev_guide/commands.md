# Install dependencies
1. uv pip install -r requirements.txt

# Run tests
1. pytest app/tests/ -v

# Run app
1. uvicorn app.main:app --reload

# Match the requirements.txt file with the current packages
1. uv pip compile requirements.txt -o uv.lock





