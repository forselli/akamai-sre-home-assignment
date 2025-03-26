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
	bin/lint.sh