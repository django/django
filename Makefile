.PHONY: build publish

build:
	rm -rf ./dist
	rm -rf ./build
	rm -rf /.eggs
	python3 setup.py sdist bdist_wheel --universal

publish:
	twine upload dist/*

build-python2:
	python2 setup.py bdist_wheel

clean:
	rm -rf build dist vba_engine.egg-info
