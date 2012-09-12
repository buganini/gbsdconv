PREFIX?=/usr/local

LIBS=-ltag

all: gbsdconv_taglib

gbsdconv_taglib: taglib/tag_c.cpp
	$(CXX) -I${PREFIX}/include/taglib -fPIC -shared -o gbsdconv_taglib.so taglib/tag_c.cpp ${LIBS}

install:
	install -m 755 gbsdconv ${PREFIX}/bin
	install -m 444 gbsdconv_taglib.so ${PREFIX}/lib
	install -m 444 gbsdconv.png gbsdconv.xml gbsdconv2.png ${PREFIX}/share

clean:
	rm -f gbsdconv_taglib.so
