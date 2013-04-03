all: sdist bdist_wheel

sdist:
	python setup.py sdist

bdist_wheel:
	python -c "import setuptools;__file__='setup.py';exec(compile(open(__file__).read().replace('\\r\\n', '\\n'), __file__, 'exec'))" bdist_wheel

.PHONY : sdist bdist_wheel
