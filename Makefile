# ============================================================
#  project-packer Makefile
#  Author: Udaya Raj Joshi
# ============================================================

# --- Version management ---
# Read version from setup.py
CURRENT_VERSION := $(shell grep -oP 'version="\K[^"]+' setup.py | head -1)

# --- Project settings ---
PROJECT_NAME    := project-packer
PACKER          := python3 packer.py
PACKED_FILE     := $(PROJECT_NAME)-$(CURRENT_VERSION).py
BACKUP_DIR      := ./backups
TIMESTAMP       := $(shell date +%Y%m%d_%H%M%S)
BACKUP_FILE     := $(BACKUP_DIR)/$(PROJECT_NAME)_backup_$(TIMESTAMP).tar.xz

# --- Python / virtual environment ---
PYTHON          := python3
PIP             := pip3
VENV_DIR        := venv
VENV_PYTHON     := $(VENV_DIR)/bin/python
VENV_PIP        := $(VENV_DIR)/bin/pip

# --- Colors for pretty output ---
RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BLUE   := \033[0;34m
CYAN   := \033[0;36m
NC     := \033[0m

# ============================================================
#  DEFAULT
# ============================================================
.PHONY: help
help:
	@echo "$(GREEN)project-packer$(NC) v$(CURRENT_VERSION)"
	@echo ""
	@echo "$(CYAN)Available targets:$(NC)"
	@echo "  $(BLUE)pack$(NC)        - Pack this project into a single .py file"
	@echo "  $(BLUE)unpack$(NC)      - Unpack a packed file (F=<file>)"
	@echo "  $(BLUE)smoke$(NC)       - End-to-end pack/unpack smoke test"
	@echo ""
	@echo "  $(BLUE)install$(NC)     - Install into a local venv (editable)"
	@echo "  $(BLUE)venv$(NC)        - Create the virtual environment"
	@echo "  $(BLUE)run$(NC)         - Show packer CLI help"
	@echo ""
	@echo "  $(BLUE)clean$(NC)       - Remove caches and build artifacts"
	@echo "  $(BLUE)distclean$(NC)   - clean + remove venv and packed files"
	@echo "  $(BLUE)dist$(NC)        - Build sdist + wheel for PyPI"
	@echo "  $(BLUE)publish$(NC)     - Upload to PyPI (needs ~/.pypirc)"
	@echo ""
	@echo "  $(BLUE)backup$(NC)      - Create a timestamped tarball of the project"
	@echo "  $(BLUE)release$(NC)     - Bump version, tag, push, create GitHub release"
	@echo "  $(BLUE)lint$(NC)        - Basic syntax + style check"
	@echo ""

# ============================================================
#  PACKING
# ============================================================
.PHONY: pack
pack:
	@echo "$(BLUE)Packing project...$(NC)"
	$(PACKER) pack . --manifest MANIFEST.in -v
	@echo "$(GREEN)Packed → $(PACKED_FILE)$(NC)"

.PHONY: unpack
unpack:
	@if [ -z "$(F)" ]; then \
		echo "$(RED)Usage: make unpack F=<packed_file>$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Unpacking $(F)...$(NC)"
	$(PACKER) unpack "$(F)" -v

# ============================================================
#  TESTING
# ============================================================
.PHONY: smoke
smoke:
	@echo "$(BLUE)Running pack/unpack smoke test...$(NC)"
	@rm -rf /tmp/packer-smoke && mkdir -p /tmp/packer-smoke
	@$(PACKER) pack . -o /tmp/packer-smoke/test.py > /dev/null
	@$(PACKER) unpack /tmp/packer-smoke/test.py /tmp/packer-smoke/unpacked > /dev/null
	@if diff -q packer.py /tmp/packer-smoke/unpacked/packer.py > /dev/null; then \
		echo "$(GREEN)✓ Round-trip OK$(NC)"; \
	else \
		echo "$(RED)✗ Round-trip FAILED$(NC)"; \
		diff packer.py /tmp/packer-smoke/unpacked/packer.py | head -20; \
		exit 1; \
	fi
	@rm -rf /tmp/packer-smoke

.PHONY: lint
lint:
	@echo "$(BLUE)Checking syntax...$(NC)"
	@$(PYTHON) -m py_compile packer.py setup.py && echo "$(GREEN)✓ Syntax OK$(NC)"
	@echo "$(BLUE)Checking for obvious issues...$(NC)"
	@$(PYTHON) -c "import ast; ast.parse(open('packer.py').read())" && echo "$(GREEN)✓ AST OK$(NC)"

# ============================================================
#  VIRTUAL ENVIRONMENT + INSTALL
# ============================================================
.PHONY: venv
venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "$(BLUE)Creating venv...$(NC)"; \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "$(GREEN)✓ venv created at $(VENV_DIR)$(NC)"; \
	else \
		echo "$(YELLOW)venv already exists$(NC)"; \
	fi

.PHONY: install
install: venv
	@echo "$(BLUE)Installing $(PROJECT_NAME) in editable mode...$(NC)"
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -e .
	@echo "$(GREEN)✓ Installed. Run: $(VENV_DIR)/bin/packer --help$(NC)"

.PHONY: run
run:
	@$(PACKER) --help

# ============================================================
#  CLEAN
# ============================================================
.PHONY: clean
clean:
	@echo "$(BLUE)Removing Python caches and build artifacts...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.so" -delete
	@rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/
	@rm -rf /tmp/packer-smoke
	@echo "$(GREEN)✓ Clean complete$(NC)"

.PHONY: distclean
distclean: clean
	@echo "$(BLUE)Removing venv and packed files...$(NC)"
	@rm -rf $(VENV_DIR)
	@rm -f $(PROJECT_NAME)-*.py
	@rm -rf $(PROJECT_NAME)-*_unpacked/
	@echo "$(GREEN)✓ Distclean complete$(NC)"

# ============================================================
#  DIST / PUBLISH
# ============================================================
.PHONY: dist
dist: clean
	@echo "$(BLUE)Building sdist and wheel...$(NC)"
	$(PYTHON) -m pip install --quiet --upgrade build
	$(PYTHON) -m build
	@echo "$(GREEN)✓ Distribution built in ./dist/$(NC)"
	@ls -lh dist/

.PHONY: publish
publish: dist
	@echo "$(YELLOW)Uploading to PyPI...$(NC)"
	$(PYTHON) -m pip install --quiet --upgrade twine
	$(PYTHON) -m twine upload dist/*
	@echo "$(GREEN)✓ Published$(NC)"

# ============================================================
#  BACKUP
# ============================================================
.PHONY: backup
backup: $(BACKUP_DIR)
	@echo "$(BLUE)Creating backup...$(NC)"
	@tar -cJf $(BACKUP_FILE) \
		--exclude='__pycache__' \
		--exclude='*.pyc' \
		--exclude='venv' \
		--exclude='.git' \
		--exclude='build' \
		--exclude='dist' \
		--exclude='*.egg-info' \
		--exclude='backups' \
		.
	@echo "$(GREEN)✓ Backup created: $(BACKUP_FILE)$(NC)"

$(BACKUP_DIR):
	@mkdir -p $(BACKUP_DIR)

# ============================================================
#  RELEASE
# ============================================================
.PHONY: release
release:
	@echo "$(GREEN)Current version: $(CURRENT_VERSION)$(NC)"
	@read -p "New version (e.g. 1.0.1, or Enter to keep current): " VERSION; \
	if [ -z "$$VERSION" ]; then VERSION=$(CURRENT_VERSION); fi; \
	echo "$(BLUE)Setting version to: $$VERSION$(NC)"; \
	sed -i 's/version="[^"]*"/version="'"$$VERSION"'"/' setup.py; \
	echo "$(BLUE)Committing and tagging...$(NC)"; \
	git add setup.py; \
	git commit -m "chore: bump version to $$VERSION" || true; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	echo "$(BLUE)Pushing...$(NC)"; \
	git push; \
	git push origin "v$$VERSION"; \
	echo "$(GREEN)✓ Released v$$VERSION$(NC)"; \
	echo "$(YELLOW)Now create the GitHub release at:$(NC)"; \
	echo "  https://github.com/blee-design/project-packer/releases/new?tag=v$$VERSION"

# ============================================================
#  SHORTCUTS
# ============================================================
.PHONY: all
all: clean pack
