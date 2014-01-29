DESTDIR?=
PREFIX?=/usr/local
LOCALBASE?=${PREFIX}

LIBS=-L${LOCALBASE}/lib -ltag

all: gbsdconv_taglib

gbsdconv_taglib: taglib/tag_c.cpp
	$(CXX) -I${LOCALBASE}/include/taglib -fPIC -shared -o gbsdconv_taglib.so taglib/tag_c.cpp ${LIBS}

install:
	install -m 755 gbsdconv ${DESTDIR}${PREFIX}/bin
	install -m 444 gbsdconv_taglib.so ${DESTDIR}${PREFIX}/lib
	mkdir -p ${DESTDIR}${PREFIX}/share/gbsdconv
	install -m 444 gbsdconv.png gbsdconv.xml gbsdconv2.png ${DESTDIR}${PREFIX}/share/gbsdconv

clean:
	rm -f gbsdconv_taglib.so
