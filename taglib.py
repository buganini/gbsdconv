from ctypes import *

taglib=CDLL('gbsdconv_taglib.so')

taglib.taglib_file_new.argtypes=[c_char_p]
taglib.taglib_file_new.restype=c_void_p

taglib.taglib_file_is_valid.argtypes=[c_void_p]
taglib.taglib_file_is_valid.restype=c_int

taglib.taglib_file_save.argtypes=[c_void_p]
taglib.taglib_file_save.restype=c_int

taglib.taglib_file_free.argtypes=[c_void_p]

taglib.taglib_mpeg_file.argtypes=[c_void_p]
taglib.taglib_mpeg_file.restype=c_void_p

taglib.taglib_mpeg_file_save3.argtypes=[c_void_p, c_int, c_bool, c_int]
taglib.taglib_mpeg_file_save3.restype=c_bool

taglib.taglib_mpeg_file_strip.argtypes=[c_void_p, c_int]
taglib.taglib_mpeg_file_strip.restype=c_bool

taglib.taglib_file_tag.argtypes=[c_void_p]
taglib.taglib_file_tag.restype=c_void_p

taglib.taglib_tag_title.argtypes=[c_void_p]
taglib.taglib_tag_title.restype=c_char_p

taglib.taglib_tag_artist.argtypes=[c_void_p]
taglib.taglib_tag_artist.restype=c_char_p

taglib.taglib_tag_album.argtypes=[c_void_p]
taglib.taglib_tag_album.restype=c_char_p

taglib.taglib_tag_comment.argtypes=[c_void_p]
taglib.taglib_tag_comment.restype=c_char_p

taglib.taglib_tag_genre.argtypes=[c_void_p]
taglib.taglib_tag_genre.restype=c_char_p

taglib.taglib_tag_year.argtypes=[c_void_p]
taglib.taglib_tag_year.restype=c_uint

taglib.taglib_tag_track.argtypes=[c_void_p]
taglib.taglib_tag_track.restype=c_uint

taglib.taglib_tag_set_title.argtypes=[c_void_p, c_char_p]
taglib.taglib_tag_set_artist.argtypes=[c_void_p, c_char_p]
taglib.taglib_tag_set_album.argtypes=[c_void_p, c_char_p]
taglib.taglib_tag_set_comment.argtypes=[c_void_p, c_char_p]
taglib.taglib_tag_set_genre.argtypes=[c_void_p, c_char_p]
