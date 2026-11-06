DESTDIR := $(HOME)/.gemini/antigravity-cli/agy-statusline
VHS_IMAGE_NAME := ghcr.io/charmbracelet/vhs

.PHONY: hooks lint format test install gif clean
.IGNORE: clean

hooks:
	@uv run pre-commit install

lint: hooks
	@uv run pre-commit run ruff-check --all-files --verbose

format: hooks
	@uv run pre-commit run ruff-format --all-files --verbose

test:
	uv run coverage run --source=statusline statusline_test.py
	uv run coverage report -m
	uv run coverage html

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
