integration-build-amd64:
	docker buildx build --platform linux/amd64 -t belay-integration-tester -f tools/Dockerfile .

integration-build:
	docker buildx build -t belay-integration-tester -f tools/Dockerfile .

integration-test:
	docker run \
		-v $(PWD):/belay \
		belay-integration-tester \
		/bin/bash -c "poetry install && poetry run python -m pytest tests/integration"

integration-bash:
	# For debugging purposes
	docker run -it \
		-v $(PWD):/belay \
		belay-integration-tester
