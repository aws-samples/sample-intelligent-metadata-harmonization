.PHONY: \
	installUv createPythonEnvironment installPythonRequirements installTypeScriptRequirements install \
	dockerCheck verifyDeployment loadEnvironmentVariables \
	bootstrap deploy destroy \
	createLocalDotEnvFile runApiLocal runUiLocal runLocal \
	testProcessor testApi testFrontend testInfrastructure testAll \
	clean cleanTypeScript cleanCloudFormation cleanMisc \
	help

#################################################################################
# INSTALL PREREQUISITES 													    #
#################################################################################

PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))


## Install uv package manager if not already installed
installUv:
	@if command -v uv >/dev/null 2>&1; then \
		echo "uv is already installed."; \
	else \
		echo "Installing uv package manager..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "uv installed successfully. Make sure it's in your PATH."; \
	fi


## Create Python environment
createPythonEnvironment: installUv
	@echo "Creating Python virtual environment with uv..."
	@uv venv .venv
	@printf "New virtual environment created. To activate run: 'source .venv/bin/activate'\n"


## Install Python dependencies
installPythonRequirements:
	@echo "Installing Python dependencies..."
	@echo "Installing metadata-harmonization-processor..."
	@cd $(PROJECT_DIR)/projects/metadata-harmonization-processor && uv pip install -e .[dev]
	@echo "Installing metadata-harmonization-api..."
	@cd $(PROJECT_DIR)/projects/api && uv pip install -e .
	@echo "Installing metadata-harmonization-agent..."
	@cd $(PROJECT_DIR)/projects/agent && uv pip install -e .
	@echo "Installing metadata-harmonization-eval..."
	@cd $(PROJECT_DIR)/projects/eval && uv pip install -e .


## Install TypeScript dependencies
installTypeScriptRequirements:
	@echo "Installing TypeScript dependencies..."
	@cd $(PROJECT_DIR)/projects/infra && npm install
	@cd $(PROJECT_DIR)/projects/frontend && npm install
	@echo "TypeScript dependencies installed successfully"


## Install all dependencies for development
install: installPythonRequirements installTypeScriptRequirements


#################################################################################
# GLOBALS                                                                       #
#################################################################################

loadEnvironmentVariables:
	@if [ ! -f "$(PROJECT_DIR)/config.yaml" ]; then \
		>&2 echo ""; \
		>&2 echo "ERROR: config.yaml not found at $(PROJECT_DIR)/config.yaml"; \
		>&2 echo ""; \
		>&2 echo "  This file is required for deployment and AWS-backed local development."; \
		>&2 echo "  Create it from the example template:"; \
		>&2 echo ""; \
		>&2 echo "    cp config.yaml.example config.yaml"; \
		>&2 echo ""; \
		>&2 echo "  Then edit config.yaml to add your personal environment section."; \
		>&2 echo "  See the README for configuration details."; \
		>&2 echo ""; \
		exit 1; \
	fi
	@echo "Loading environment variables..."
	@$(eval ENV := $(shell cat $(PROJECT_DIR)/config.yaml 2>/dev/null | yq -r '.env // ""' 2>/dev/null))
	@if [ -z "$(ENV)" ]; then \
		>&2 echo "ERROR: ENV must be set in config.yaml"; \
		exit 1; \
	fi

	@$(eval APP_NAME := $(shell cat $(PROJECT_DIR)/config.yaml 2>/dev/null | yq -r '.appName // ""' 2>/dev/null))
	@if [ -z "$(APP_NAME)" ]; then \
		>&2 echo "ERROR: APP_NAME must be set in config.yaml"; \
		exit 1; \
	fi

	@$(eval PROFILE := $(if $(PROFILE),$(PROFILE),$(shell cat $(PROJECT_DIR)/config.yaml 2>/dev/null | yq -r '.$(ENV).profile // ""' 2>/dev/null)))
	@if [ -z "$(PROFILE)" ]; then \
		>&2 echo "WARNING: PROFILE is not set in config.yaml or command line"; \
	fi

	@$(eval DEPLOYMENT_NAME := $(if $(DEPLOYMENT_NAME),$(DEPLOYMENT_NAME),$(shell cat $(PROJECT_DIR)/config.yaml 2>/dev/null | yq -r '.$(ENV).deploymentName // ""' 2>/dev/null)))
	@if [ -z "$(DEPLOYMENT_NAME)" ]; then \
		>&2 echo "ERROR: DEPLOYMENT_NAME must be set in config.yaml or command line"; \
		exit 1; \
	fi

	@$(eval ACCOUNT_NUMBER := $(if $(ACCOUNT_NUMBER),$(ACCOUNT_NUMBER),$(shell cat $(PROJECT_DIR)/config.yaml 2>/dev/null | yq -r '.$(ENV).accountNumber // ""' 2>/dev/null)))
	@if [ -z "$(ACCOUNT_NUMBER)" ]; then \
		>&2 echo "ERROR: ACCOUNT_NUMBER must be set in config.yaml or command line"; \
		exit 1; \
	fi

	@$(eval REGION := $(if $(REGION),$(REGION),$(shell cat $(PROJECT_DIR)/config.yaml 2>/dev/null | yq -r '.$(ENV).region // ""' 2>/dev/null)))
	@if [ -z "$(REGION)" ]; then \
		>&2 echo "ERROR: REGION must be set in config.yaml or command line"; \
		exit 1; \
	fi

	@$(eval DEPLOYMENT_STAGE := $(shell cat $(PROJECT_DIR)/config.yaml 2>/dev/null | yq -r '.$(ENV).deploymentStage // ""' 2>/dev/null))
	@if [ -z "$(DEPLOYMENT_STAGE)" ]; then \
		>&2 echo "ERROR: DEPLOYMENT_STAGE must be set in config.yaml"; \
		exit 1; \
	fi

	@$(eval LOG_LEVEL := $(shell cat $(PROJECT_DIR)/config.yaml 2>/dev/null | yq -r '.$(ENV).logLevel // ""' 2>/dev/null))
	@if [ -z "$(LOG_LEVEL)" ]; then \
		>&2 echo "ERROR: LOG_LEVEL must be set in config.yaml"; \
		exit 1; \
	fi

	@$(eval TARGET_PLATFORM := $(shell cat $(PROJECT_DIR)/config.yaml 2>/dev/null | yq -r '.$(ENV).targetPlatform // ""' 2>/dev/null))
	@if [ -z "$(TARGET_PLATFORM)" ]; then \
		>&2 echo "ERROR: TARGET_PLATFORM must be set in config.yaml"; \
		exit 1; \
	fi

	@echo "Environment variables loaded successfully"


##############################################################################
# RULES                                                                      #
##############################################################################

## Bootstrap AWS Account with CDK bootstrap
bootstrap: loadEnvironmentVariables
	@printf "Bootstrapping: $(ACCOUNT_NUMBER) | $(REGION)\n"
	@cd ${PROJECT_DIR}/projects/infra && npx cdk bootstrap \
		$(if ${PROFILE}, --profile ${PROFILE}) \
		aws://$(ACCOUNT_NUMBER)/$(REGION) \
		--cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess


## Delete all local compiled Python files and related artifacts
cleanPython:
	@find . -type f -name "*.py[co]" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@find . -type d -name "dist" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@find . -type d -name ".tox" -exec rm -rf {} +



## Delete local TypeScript artifacts and related folders
cleanTypeScript:
	@find . -type f -name "*.js.map" -delete
	@find . -type f -name ".package-lock.json" -delete
	@find . -type f -name "env.js" -delete
	@find . -type d -name "node_modules" -exec rm -rf {} +
	@find . -type d -name "dist" -exec rm -rf {} +
	@find . -type d -name ".next" -exec rm -rf {} +
	@find . -type d -name "build" -exec rm -rf {} +
	@find . -type d -name ".tscache" -exec rm -rf {} +
	@find . -type d -name ".jest_cache" -exec rm -rf {} +
	@find . -type d -name "out" -exec rm -rf {} +
	@rm -rf $(PROJECT_DIR)/frontend/.next $(PROJECT_DIR)/frontend/out


## Delete local CloudFormation outputs
cleanCloudFormation:
	@find . -type d -name "cdk.out" -exec rm -rf {} +


## Delete all local misc files
cleanMisc:
	@find . -type f -name "*.DS_Store" -delete
	@find . -type f -name "*repomix*" -delete
	@find . -type f -name "*.env*" -delete


## Run all local clean commands to delete local files
clean: cleanCloudFormation cleanMisc cleanTypeScript cleanPython


## Make sure Docker is running
dockerCheck:
	@cmd_output=$$(docker ps); \
	if \
		[ $$? != 0 ]; \
		then \
			echo $$cmd_output; \
			exit 1; \
	fi;


## Verify deployment
verifyDeployment: loadEnvironmentVariables
	@printf "Verifying deployment with environment: ${ENV}\n"
	@$(if $(PROFILE),AWS_PROFILE=$(PROFILE)) bash -c '\
		if [ -f $(PROJECT_DIR)/.env ]; then set -a; source $(PROJECT_DIR)/.env; set +a; fi; \
		uv run python $(PROJECT_DIR)/scripts/verify_deployment.py'


## Test infrastructure deployment in development environment
testInfrastructureDeployment: loadEnvironmentVariables
	@printf "Testing infrastructure deployment with environment: ${ENV}\n"
	@$(if $(PROFILE),AWS_PROFILE=$(PROFILE)) uv run python $(PROJECT_DIR)/scripts/test_infrastructure_deployment.py


## Test the metadata harmonization processor package
testProcessor:
	@echo "Running metadata harmonization processor tests..."
	@cd $(PROJECT_DIR)/projects/metadata-harmonization-processor && uv run pytest tests/ -v


## Test the API package
testApi:
	@echo "Running API tests..."
	@cd $(PROJECT_DIR)/projects/api && uv run pytest tests/ -v


## Test the evaluation package
testEval:
	@echo "Running evaluation tests..."
	@cd $(PROJECT_DIR)/projects/eval && uv run pytest tests/ -v


## Test the frontend package
testFrontend:
	@echo "Running frontend tests..."
	@cd $(PROJECT_DIR)/projects/frontend && npm test


## Test the infrastructure package
testInfrastructure:
	@echo "Running infrastructure tests..."
	@cd $(PROJECT_DIR)/projects/infra && npm test


## Run all tests with combined summary
testAll:
	@failed=""; \
	echo "========================================="; \
	echo "  RUNNING ALL TEST SUITES"; \
	echo "========================================="; \
	echo ""; \
	echo "--- [1/5] Processor ---"; \
	(cd $(PROJECT_DIR)/projects/metadata-harmonization-processor && uv run pytest tests/ -v) || failed="$$failed processor"; \
	echo ""; \
	echo "--- [2/5] API ---"; \
	(cd $(PROJECT_DIR)/projects/api && uv run pytest tests/ -v) || failed="$$failed api"; \
	echo ""; \
	echo "--- [3/5] Eval ---"; \
	(cd $(PROJECT_DIR)/projects/eval && uv run pytest tests/ -v) || failed="$$failed eval"; \
	echo ""; \
	echo "--- [4/5] Frontend ---"; \
	(cd $(PROJECT_DIR)/projects/frontend && npm test) || failed="$$failed frontend"; \
	echo ""; \
	echo "--- [5/5] Infrastructure ---"; \
	(cd $(PROJECT_DIR)/projects/infra && npm test) || failed="$$failed infra"; \
	echo ""; \
	echo "========================================="; \
	if [ -z "$$failed" ]; then \
		echo "  ALL TEST SUITES PASSED (5/5)"; \
	else \
		echo "  FAILED SUITES:$$failed"; \
		echo "========================================="; \
		exit 1; \
	fi; \
	echo "========================================="


## Run evaluation on dataset(s) - automatically detects file vs directory
runEval:
	@if [ -z "$(PATH_OR_FILTER)" ]; then \
		echo "ERROR: Specify PATH_OR_FILTER=<path or filter>"; \
		echo ""; \
		echo "Examples:"; \
		echo "  Single file:  make runEval PATH_OR_FILTER=data/synthetic_dataset/synthetic_cyclospora_dataset_1_err40.csv"; \
		echo "  Directory:    make runEval PATH_OR_FILTER=data/synthetic_dataset"; \
		echo "  Error filter: make runEval PATH_OR_FILTER=err40"; \
		echo ""; \
		echo "Optional: Add ARGS='--verbose --format json' for additional options"; \
		echo "Config:   Uses projects/eval/config.yaml by default for pricing and settings"; \
		exit 1; \
	fi
	@if [ -f "$(PATH_OR_FILTER)" ]; then \
		echo "Running evaluation on file: $(PATH_OR_FILTER)"; \
		uv run mh-eval -c projects/eval/config.yaml $(PATH_OR_FILTER) $(ARGS); \
	elif [ -d "$(PATH_OR_FILTER)" ]; then \
		echo "Running batch evaluation on directory: $(PATH_OR_FILTER)"; \
		uv run mh-eval -c projects/eval/config.yaml --auto-discover $(PATH_OR_FILTER) --batch $(ARGS); \
	else \
		echo "Running filtered evaluation: $(PATH_OR_FILTER)"; \
		uv run mh-eval -c projects/eval/config.yaml --auto-discover data/synthetic_dataset --error-rate-filter $(PATH_OR_FILTER) --batch $(ARGS); \
	fi


## Create local .env file for development
createLocalDotEnvFile: loadEnvironmentVariables
	@echo "Generating new .env file..."
	@$(eval DEFAULT_STACK_NAME := $(DEPLOYMENT_NAME)-$(APP_NAME)-$(DEPLOYMENT_STAGE))
	@$(eval STACK_NAME := $(if $(STACK_NAME),$(STACK_NAME),$(DEFAULT_STACK_NAME)))
	@if [ ! -f ${PROJECT_DIR}/scripts/generate_dotenv.sh ]; then echo "ERROR: Script for generating .env file not found."; exit 1; fi
	@$(if $(PROFILE),AWS_PROFILE=$(PROFILE)) bash ${PROJECT_DIR}/scripts/generate_dotenv.sh "$(STACK_NAME)" "$(REGION)" "$(PROFILE)" "$(LOG_LEVEL)"


## Run the REST API locally for development
runApiLocal: createLocalDotEnvFile
	@if [ -z "$(ENABLE_AUTH)" ]; then \
		echo "WARNING: ENABLE_AUTH is not set. Defaulting to false."; \
		ENABLE_AUTH=false; \
	fi; \
	$(if $(PROFILE),AWS_PROFILE=$(PROFILE)) API_ENABLE_AUTH=$${ENABLE_AUTH:-$(ENABLE_AUTH)} bash ${PROJECT_DIR}/projects/infra/lib/api/entrypoint.sh


## Run dev UI locally
runUiLocal: loadEnvironmentVariables
	@echo "Generating new env.js file..."
	@$(eval DEFAULT_STACK_NAME := $(DEPLOYMENT_NAME)-$(APP_NAME)-$(DEPLOYMENT_STAGE))
	@$(eval STACK_NAME := $(if $(STACK_NAME),$(STACK_NAME),$(DEFAULT_STACK_NAME)))
	@if [ ! -f ${PROJECT_DIR}/scripts/generate_envjs.sh ]; then echo "ERROR: Script for generating env.js file not found."; exit 1; fi
	@$(if $(PROFILE),AWS_PROFILE=$(PROFILE)) bash ${PROJECT_DIR}/scripts/generate_envjs.sh "$(STACK_NAME)" "$(REGION)" "$(PROFILE)" "$(LOG_LEVEL)"
	@npm run dev --prefix $(PROJECT_DIR)/projects/frontend


## Run both API and UI services locally with synchronized startup and shutdown for full stack development
runLocal:
	@echo "Starting both API and UI services together for full stack development..."
	@bash $(PROJECT_DIR)/scripts/run_local.sh


## Deploy all infrastructure
deploy: loadEnvironmentVariables dockerCheck cleanMisc
	@printf "\n \
	DEPLOYING ALL APP INFRASTRUCTURE \n \
	-----------------------------------\n \
	Deployment Profile     ${PROFILE}\n \
	Account Number         ${ACCOUNT_NUMBER}\n \
	Region                 ${REGION}\n \
	App Name               ${APP_NAME}\n \
	Deployment Stage       ${DEPLOYMENT_STAGE}\n \
	Deployment Name        ${DEPLOYMENT_NAME}\n \
	-----------------------------------\n \
	Is the configuration correct? [y/N]:  "\
	&& read confirm_config &&\
	if \
		[ $${confirm_config:-'N'} = 'y' ]; \
		then \
			$(MAKE) verifyDeployment &&\
			export DOCKER_DEFAULT_PLATFORM=$(TARGET_PLATFORM) &&\
			cd ${PROJECT_DIR}/projects/infra && npx cdk deploy ${DEPLOYMENT_STAGE}/* \
				$(if ${PROFILE}, --profile ${PROFILE}) \
				-c ${ENV}='$(shell echo '${${ENV}}')'; \
	fi;


## Tear down all infrastructure
destroy: loadEnvironmentVariables cleanMisc
	@printf "\n \
	DESTROYING ALL APP INFRASTRUCTURE \n \
	-----------------------------------\n \
	Deployment Profile     ${PROFILE}\n \
	Account Number         ${ACCOUNT_NUMBER}\n \
	Region                 ${REGION}\n \
	App Name               ${APP_NAME}\n \
	Deployment Stage       ${DEPLOYMENT_STAGE}\n \
	Deployment Name        ${DEPLOYMENT_NAME}\n \
	-----------------------------------\n \
	Is the configuration correct? [y/N]:  "\
	&& read confirm_config &&\
	if \
		[ $${confirm_config:-'N'} = 'y' ]; \
		then \
			cd ${PROJECT_DIR}/projects/infra && npx cdk destroy ${DEPLOYMENT_STAGE}/* \
				--force \
				$(if ${PROFILE}, --profile ${PROFILE}); \
	fi;


##############################################################################
# SELF DOCUMENTING RULES                                                     #
##############################################################################

.DEFAULT_GOAL := help
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=35 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')
