download-firmware:
	@echo "Downloading firmware files for integration tests..."
	@mkdir -p rp2040js
	curl -L https://micropython.org/resources/firmware/RPI_PICO-20210902-v1.17.uf2 -o rp2040js/micropython-v1.17.uf2
	curl -L https://downloads.circuitpython.org/bin/raspberry_pi_pico/en_US/adafruit-circuitpython-raspberry_pi_pico-en_US-7.3.3.uf2 -o rp2040js/circuitpython-v7.3.3.uf2
	curl -L https://downloads.circuitpython.org/bin/raspberry_pi_pico/en_US/adafruit-circuitpython-raspberry_pi_pico-en_US-8.0.0.uf2 -o rp2040js/circuitpython-v8.0.0.uf2
	@echo "Firmware download complete!"

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
