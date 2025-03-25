VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

# Default values for flags
VIOLATION ?= 
MULTIPLIER ?= 1.5
MAX_MESSAGES ?= 0

# Build flag arguments based on variables
VIOLATION_FLAG = $(if $(VIOLATION),--violation,)
MULTIPLIER_FLAG = --multiplier=$(MULTIPLIER)
MAX_MESSAGES_FLAG = --max-messages=$(MAX_MESSAGES)

.PHONY: run run-violation clean

# Standard run target
run: $(VENV)/bin/activate
	$(PYTHON) src/simulate_data.py $(MAX_MESSAGES_FLAG)

# Convenience target to enable violation mode
run-violation: $(VENV)/bin/activate
	$(PYTHON) src/simulate_data.py --violation $(MULTIPLIER_FLAG) $(MAX_MESSAGES_FLAG)

# Create and initialize virtual environment
$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

clean:
	rm -rf **__pycache__**
	rm -rf $(VENV)