# Tags cannot contain plus sign:
# https://docs.docker.com/engine/reference/commandline/tag/
TAG := $(shell git describe --tags --dirty | tr + -)

ifdef $(out)
        OUT_DIR := $(out):/output
else
        OUT_DIR := /tmp/alphafold:/output
endif

all: docker2singularity

docker_build:
	docker build -f docker/Dockerfile -t alphafold:$(TAG) .

docker2singularity: docker_build
	docker run -v /var/run/docker.sock:/var/run/docker.sock -v $(OUT_DIR) \
		--privileged -t --rm \
		quay.io/singularity/docker2singularity \
		--name alphafold_$(TAG).sif \
		alphafold:$(TAG)
