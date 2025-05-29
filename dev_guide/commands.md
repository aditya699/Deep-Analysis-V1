# Install dependencies
1. uv pip install -r requirements.txt

# Run tests
1. pytest app/tests/ -v

# Run app
1. uvicorn app.main:app --reload

# Match the requirements.txt file with the current packages
1. uv pip compile requirements.txt -o uv.lock

# Commands to run the openai container
1. python -m app.container.utils


# Commands for docker(Just follow this if u want to just run the app)
1.docker build -t deep-analysis .

2.docker run -d -p 8000:8000 deep-analysis
