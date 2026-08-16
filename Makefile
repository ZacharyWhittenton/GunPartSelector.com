.PHONY: setup frontend-install backend-install infra-install test test-frontend test-backend test-infra build build-frontend package-backend frontend-dev backend-dev

setup: frontend-install backend-install infra-install

frontend-install:
	python3 scripts/project.py frontend-install

backend-install:
	python3 scripts/project.py backend-install

infra-install:
	python3 scripts/project.py infra-install

test:
	python3 scripts/project.py test

test-frontend:
	python3 scripts/project.py test-frontend

test-backend:
	python3 scripts/project.py test-backend

test-infra:
	python3 scripts/project.py test-infra

build:
	python3 scripts/project.py build

build-frontend:
	python3 scripts/project.py build-frontend

package-backend:
	python3 scripts/package_lambda.py

frontend-dev:
	python3 scripts/project.py frontend-dev

backend-dev:
	python3 scripts/project.py backend-dev
