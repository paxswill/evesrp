#!/bin/sh
# Inspired by
# http://sleepycoders.blogspot.com/2013/03/sharing-travis-ci-generated-files.html
# with a few minor changes (namely the messages and the automatic rebasing).

if [ "$TRAVIS_PULL_REQUEST" = "false" ]; then
	printf "Starting test report update.\n"

	# Set up git
	git config --global user.email "travis@travis-ci.org"
	git config --global user.name "Travis"

	cd gh-pages
	git add .
	git commit -m "Travis job ${TRAVIS_JOB_NUMBER} test results"

	printf "Attempting to push to GitHub..."
	local GIT_URL="https://${GH_TOKEN}@github.com/paxswill/evesrp.git"
	while ! git push -q "${GIT_URL}" gh-pages >/dev/null 2>&1; do
		printf "rebasing..."
		git pull -r origin gh-pages
	done
	printf "done!\n"
fi
