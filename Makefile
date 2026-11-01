DESTDIR := $(HOME)/.gemini/antigravity-cli/agy-statusline
VHS_IMAGE_NAME := ghcr.io/charmbracelet/vhs

.PHONY: test install gif clean
.IGNORE: clean

test:
	uv run --with coverage coverage run --source=statusline statusline_test.py
	uv run --with coverage coverage report -m
	uv run --with coverage coverage html

install:
	mkdir -p $(DESTDIR)
	cp statusline.py statusline.sh $(DESTDIR)/

gif:
	docker run --rm \
		--volume "$(CURDIR):/vhs" \
		--env PYTHONDONTWRITEBYTECODE=1 \
		$(VHS_IMAGE_NAME) vhs/statusline.tape

clean:
	docker image rm $(VHS_IMAGE_NAME)
	rm -rf __pycache__ .coverage htmlcov
