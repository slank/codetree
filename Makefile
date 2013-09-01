userinstall:
	python setup.py install --user

install:
	python setup.py install

clean:
	rm -rf build codetree.egg-info dist
	find . -name \*.pyc -delete

test:
	nosetests tests/
