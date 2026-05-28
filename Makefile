##############################################################################
# Already Here Command OS — Developer Task Runner
#
# Usage:
#   make lint          — ruff + isort + flake8 + mypy
#   make security      — bandit + semgrep + key-check
#   make test-unit     — unit tests only (< 30s)
#   make test-int      — integration tests (needs running backend)
#   make test-e2e      — Playwright E2E (needs live server)
#   make test-reg      — regression smoke tests
#   make test          — all tests sequentially (CI order)
#   make ci            — full CI pipeline locally
#   make clean         — remove __pycache__, .pytest_cache, coverage files
##############################################################################

PYTHON     := python3
PIP        := pip
PYTEST     := pytest
BACKEND    := backend
TEST_ARGS  := --tb=short --no-header -q

.PHONY: lint security test-unit test-int test-e2e test-reg test ci clean \
        format install install-dev check-keys

# ── Install ───────────────────────────────────────────────────────────────────

install:
	$(PIP) install -r $(BACKEND)/requirements.txt

install-dev:
	$(PIP) install -r $(BACKEND)/requirements.txt
	$(PIP) install ruff bandit safety pip-audit semgrep playwright pytest-playwright
	playwright install chromium

# ── Linting / Static Analysis ─────────────────────────────────────────────────

lint:
	@echo "==> ruff"
	cd $(BACKEND) && ruff check . --output-format=text
	@echo "==> isort check"
	cd $(BACKEND) && isort . --check-only --diff
	@echo "==> flake8"
	cd $(BACKEND) && flake8 . \
		--max-line-length=120 \
		--extend-ignore=E203,W503,E501 \
		--exclude=__pycache__,.git,migrations,tests \
		--count
	@echo "==> mypy (informational)"
	-cd $(BACKEND) && mypy . \
		--ignore-missing-imports \
		--exclude 'tests|migrations|__pycache__|emergentintegrations' \
		--no-error-summary

format:
	cd $(BACKEND) && ruff format .
	cd $(BACKEND) && isort .

# ── Security Scanning ────────────────────────────────────────────────────────

security: check-keys
	@echo "==> bandit"
	-cd $(BACKEND) && bandit -r . -x tests,migrations -ll --format txt
	@echo "==> pip-audit"
	-pip-audit -r $(BACKEND)/requirements.txt
	@echo "==> semgrep"
	-semgrep scan --config .semgrep.yml $(BACKEND)/ --error --exclude "tests/"

check-keys:
	@echo "==> checking for hardcoded API keys"
	@if grep -rn --include="*.py" --include="*.yml" --include="*.json" \
		-E '(sk_live_[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{30,}|AIza[a-zA-Z0-9]{30,})' \
		--exclude-dir=.git --exclude-dir=node_modules .; then \
		echo "FAIL: Live API key found in repo!"; exit 1; \
	else \
		echo "PASS: No live keys detected."; \
	fi

# ── Tests ────────────────────────────────────────────────────────────────────

test-unit:
	@echo "==> Unit tests"
	cd $(BACKEND) && $(PYTEST) tests/unit/ $(TEST_ARGS) -v

test-int:
	@echo "==> Integration tests"
	cd $(BACKEND) && \
		STORAGE_BACKEND=sqlite SQLITE_PATH=/tmp/test_ci.db \
		STRIPE_API_KEY=sk_test_emergent \
		$(PYTEST) tests/integration/ $(TEST_ARGS) -v

test-e2e:
	@echo "==> E2E tests (Playwright)"
	cd $(BACKEND) && \
		$(PYTEST) tests/e2e/ $(TEST_ARGS) --browser chromium -v

test-reg:
	@echo "==> Regression tests"
	cd $(BACKEND) && $(PYTEST) tests/regression/ $(TEST_ARGS) -v

test-live:
	@echo "==> Live backend tests (backend_test.py)"
	cd $(BACKEND) && $(PYTEST) tests/backend_test.py $(TEST_ARGS) -v

# Run tests sequentially in CI order
test: test-unit test-int test-reg
	@echo "==> All non-E2E tests passed"

# Full CI pipeline locally (includes E2E)
ci: lint security test-unit test-int test-e2e test-reg
	@echo "==> Full CI pipeline complete"

# ── Helpers ──────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	rm -f test_reports/*.xml 2>/dev/null || true
	@echo "Cleaned."

# Run cycle on live server
cycle:
	curl -X POST https://app.alreadyherellc.com/api/cycle/run | python3 -m json.tool

# Show live connector status
connectors:
	curl https://app.alreadyherellc.com/api/cycle/connectors | python3 -m json.tool

# SSH to OCI server
ssh:
	ssh -i ~/.ssh/oci_cmdos_oci ubuntu@129.146.236.177
