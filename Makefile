build:
	docker build -t app:forselli .

kind: build
	bin/deploy-kind.sh

kind-rm:
	kind delete cluster

docker-compose:
	docker-compose up -d --build

docker-compose-rm:
	docker-compose down