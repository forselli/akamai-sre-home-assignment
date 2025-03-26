#!/bin/bash
set -e

ruff check app/src --ignore E501
