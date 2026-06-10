build-DependenciesLayer:
	pip install numpy opencv-python-headless Pillow -t $(ARTIFACTS_DIR)/python/
	find $(ARTIFACTS_DIR)/python -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
	find $(ARTIFACTS_DIR)/python -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find $(ARTIFACTS_DIR)/python -name "*.pyc" -delete 2>/dev/null || true
