.PHONY: install, clean, pypi

install:
	uv pip install -e ".[dev]" 

clean:
	rm -rf .pytest_cache
	rm -rf */__pycache__

pypi: clean
	uv build
	uv publish
