DESTDIR ?= $(HOME)/.gemini/antigravity-cli/agy-statusline

.PHONY: test install

test:
	uv run --with coverage coverage run --source=statusline statusline_test.py
	uv run --with coverage coverage report -m
	uv run --with coverage coverage html

install:
	mkdir -p $(DESTDIR)
	cp statusline.py statusline_test.py statusline.sh $(DESTDIR)/
