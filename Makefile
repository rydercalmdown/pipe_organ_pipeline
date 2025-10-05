run:
	uv run python pipeline.py originals/mrbrightside.mp3

install:
	uv sync

.PHONY: run install
