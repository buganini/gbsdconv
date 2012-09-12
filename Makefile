PREFIX?=/usr/local

LIBS=-ltag

all: gbsdconv_taglib

gbsdconv_taglib: taglib/tag_c.cpp
	$(CXX) -I${PREFIX}/include/taglib -fPIC -shared -o gbsdconv_taglib.so taglib/tag_c.cpp ${LIBS}
