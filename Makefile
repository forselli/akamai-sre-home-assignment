build:
	docker build -t app:forselli .

deploy-kind: build
	bin/deploy-kind.sh

delete-kind:
	kind delete cluster

deploy-docker-compose:
	docker-compose up -d --build

delete-docker-compose:
	docker-compose down