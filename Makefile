doc:
	sphinx-apidoc -f -o ./rst/apidoc ./collections_undo
	sphinx-build -b html ./rst ./docs

release:
	python setup.py sdist
	python setup.py bdist_wheel
	twine upload --repository testpypi dist/*
	twine upload --repository pypi dist/*
