build:
	docker build -t my-registry:5001/app:latest .

kind: build
	bin/deploy-kind.sh

kind-rm:
	kind delete cluster

docker-compose:
	docker-compose up -d --build

docker-compose-rm:
	docker-compose down

lint:
	poetry run ruff check app/src

test:
	PYTHONPATH="app/src:app/tests" poetry run pytest
