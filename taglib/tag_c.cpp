/***************************************************************************
    copyright            : (C) 2003 by Scott Wheeler
    email                : wheeler@kde.org
 ***************************************************************************/

/***************************************************************************
 *   This library is free software; you can redistribute it and/or modify  *
 *   it  under the terms of the GNU Lesser General Public License version  *
 *   2.1 as published by the Free Software Foundation.                     *
 *                                                                         *
 *   This library is distributed in the hope that it will be useful, but   *
 *   WITHOUT ANY WARRANTY; without even the implied warranty of            *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU     *
 *   Lesser General Public License for more details.                       *
 *                                                                         *
 *   You should have received a copy of the GNU Lesser General Public      *
 *   License along with this library; if not, write to the Free Software   *
 *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
 *   USA                                                                   *
 ***************************************************************************/


#include <fileref.h>
#include <tfile.h>
#include <tag.h>
#include <mpegfile.h>
#include <id3v2header.h>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "tag_c.h"

using namespace TagLib;
static thread_local std::vector<char *> strings;

static FileRef *ref(TagLib_File *file) { return reinterpret_cast<FileRef *>(file); }
static Tag *tag(TagLib_Tag *value) { return reinterpret_cast<Tag *>(value); }
static char *copy_string(const String &value) {
    char *result = ::strdup(value.toCString(true));
    if(result) strings.push_back(result);
    return result;
}

TagLib_File *taglib_file_new(const char *filename) {
    auto *file = new FileRef(filename);
    if(file->isNull()) { delete file; return nullptr; }
    return reinterpret_cast<TagLib_File *>(file);
}
void taglib_file_free(TagLib_File *file) { delete ref(file); }
BOOL taglib_file_is_valid(const TagLib_File *file) {
    return file && !reinterpret_cast<const FileRef *>(file)->isNull();
}
TagLib_Tag *taglib_file_tag(const TagLib_File *file) {
    return reinterpret_cast<TagLib_Tag *>(reinterpret_cast<const FileRef *>(file)->tag());
}
BOOL taglib_file_save(TagLib_File *file) { return ref(file)->save(); }

char *taglib_tag_title(const TagLib_Tag *value) { return copy_string(reinterpret_cast<const Tag *>(value)->title()); }
char *taglib_tag_artist(const TagLib_Tag *value) { return copy_string(reinterpret_cast<const Tag *>(value)->artist()); }
char *taglib_tag_album(const TagLib_Tag *value) { return copy_string(reinterpret_cast<const Tag *>(value)->album()); }
char *taglib_tag_comment(const TagLib_Tag *value) { return copy_string(reinterpret_cast<const Tag *>(value)->comment()); }
char *taglib_tag_genre(const TagLib_Tag *value) { return copy_string(reinterpret_cast<const Tag *>(value)->genre()); }
unsigned int taglib_tag_year(const TagLib_Tag *value) { return reinterpret_cast<const Tag *>(value)->year(); }
unsigned int taglib_tag_track(const TagLib_Tag *value) { return reinterpret_cast<const Tag *>(value)->track(); }
void taglib_tag_set_title(TagLib_Tag *value, const char *text) { tag(value)->setTitle(String(text, String::UTF8)); }
void taglib_tag_set_artist(TagLib_Tag *value, const char *text) { tag(value)->setArtist(String(text, String::UTF8)); }
void taglib_tag_set_album(TagLib_Tag *value, const char *text) { tag(value)->setAlbum(String(text, String::UTF8)); }
void taglib_tag_set_comment(TagLib_Tag *value, const char *text) { tag(value)->setComment(String(text, String::UTF8)); }
void taglib_tag_set_genre(TagLib_Tag *value, const char *text) { tag(value)->setGenre(String(text, String::UTF8)); }
void taglib_tag_free_strings() { for(auto *value : strings) std::free(value); strings.clear(); }

TagLib_Mpeg_File *taglib_mpeg_file(TagLib_File *file) {
    return reinterpret_cast<TagLib_Mpeg_File *>(dynamic_cast<MPEG::File *>(ref(file)->file()));
}
BOOL taglib_mpeg_file_save3(TagLib_Mpeg_File *file, int tags, BOOL stripOthers, int version) {
    return reinterpret_cast<MPEG::File *>(file)->save(tags,
        stripOthers ? MPEG::File::StripOthers : MPEG::File::StripNone,
        version == 3 ? ID3v2::v3 : ID3v2::v4);
}
BOOL taglib_mpeg_file_strip(TagLib_Mpeg_File *file, int tags) {
    return reinterpret_cast<MPEG::File *>(file)->strip(tags);
}
