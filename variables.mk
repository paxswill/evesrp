PROJECT_ROOT := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
STATIC_DIR := src/evesrp/static
NODE_MODULES := $(shell npm root)
NODE_BIN := $(shell npm bin)
