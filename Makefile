# Makefile for the Project Packer tool (packer.py)

PROJECT_NAME := project-packer
PACKED_FILE := $(PROJECT_NAME)-bundled.py
PACKER_CMD := python packer.py

# Default target
all: pack

# ---------------------------------------------------------------------
# Pack the project (including all files) into a single file
# This is useful for creating a self-contained version of the packer.
# ---------------------------------------------------------------------
pack:
	$(PACKER_CMD) pack . -o $(PACKED_FILE) -v --all-files

# ---------------------------------------------------------------------
# Unpack the previously packed file (for testing)
# ---------------------------------------------------------------------
unpack:
	$(PACKER_CMD) unpack $(PACKED_FILE) -v

# ---------------------------------------------------------------------
# Clean up all generated files, cache, and build artifacts
# ---------------------------------------------------------------------
clean:
	rm -rf dist/ build/ *.egg-info/ __pycache__/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*~" -delete
	find . -name "*.bak" -delete
	rm -f $(PACKED_FILE)
	rm -f *.pyc

# ---------------------------------------------------------------------
# Build source distribution and wheel
# ---------------------------------------------------------------------
dist: clean
	python setup.py sdist bdist_wheel

# ---------------------------------------------------------------------
# Install the package locally (in development mode)
# ---------------------------------------------------------------------
install:
	pip install -e .

# ---------------------------------------------------------------------
# Run a simple test: import the packer module and show help
# ---------------------------------------------------------------------
test:
	@echo "Running import test..."
	python -c "import packer; print('✅ Import successful')"
	@echo "Showing help:"
	python packer.py --help

# ---------------------------------------------------------------------
# Create a distribution and then install it (for release testing)
# ---------------------------------------------------------------------
release: clean dist
	pip install dist/*.whl

# ---------------------------------------------------------------------
# Pack the project and then unpack it to verify round‑trip
# ---------------------------------------------------------------------
roundtrip: pack unpack
	@echo "✅ Round‑trip completed: packed and unpacked successfully"

.PHONY: all pack unpack clean dist install test release roundtrip
