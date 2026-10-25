PYTHON?=python3

all:
	$(PYTHON) setup.py build_ext --inplace

install:
	$(PYTHON) -m pip install .

check:
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m unittest discover -s tests -v

clean:
	rm -rf build
	rm -f src/_taglib*.so src/_taglib*.pyd
