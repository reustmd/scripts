#requires pyexiv2
#brew install exiv2 pyexiv2
#if not using python from brew, will need to update path: export PYTHONPATH=/opt/boxen/homebrew/lib/python2.7/site-packages:$PYTHONPATH

import os
import ntpath
import sys
import pyexiv2
import subprocess
import datetime

#could be faster if needed: http://stackoverflow.com/a/947239
def get_creation_time(path):
    p = subprocess.Popen(['stat', '-f%B', path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.wait():
        raise OSError(p.stderr.read().rstrip())
    else:
        return datetime.datetime.fromtimestamp(int(p.stdout.read()))

def is_root_year_directory(directory_name):

    return directory_name.isdigit() and (1900 < int(directory_name) < 2100)


def is_photo_file(file_name):

    file_name_lowered = file_name.lower()

    for file_extension in [".png", ".gift", ".jpg", ".jpeg", ".tiff", ".bmp"]:
        if file_extension in file_name_lowered:
            return True

    return False


def ensure_lower_case_file_name(full_file_path):

    file_name = ntpath.basename(full_file_path)
    file_name_lowered = file_name.lower()

    if file_name == file_name_lowered:
        return

    new_full_file_path = full_file_path.replace(file_name, file_name_lowered)

    print "Renaming file from: '{0}' to: '{1}'".format(full_file_path, new_full_file_path)
    os.rename(full_file_path, new_full_file_path)


#Checks if file stored with an elder directory representing the year
# example: /somewhere/photos-root/2014/album/my-pic.jpeg --> 2014
def exit_with_error(error_message):
    print error_message
    sys.exit(1)


def get_elder_year_directory(full_file_path):
    directories = ntpath.dirname(full_file_path).split(os.sep)

    potential_elder_year_directories = [directory for directory in directories if is_root_year_directory(directory)]

    if len(potential_elder_year_directories) == 0:
        return None

    if len(potential_elder_year_directories) == 1:
        return int(potential_elder_year_directories[0])

    exit_with_error("Error, unexpected state.  Detected more than 1 elder year directory for the path: " + full_file_path)


def print_date_taken_exif_contradicts_elder_year_folder(full_file_path):
    photo_year = get_elder_year_directory(full_file_path)

    if not photo_year:
        return

    file_date_taken = get_date_taken(full_file_path)

    if file_date_taken.year != photo_year:
        print "Exif probably wrong, elder folder year: {0}, Date taken: {1}, Full path: {2}".format(photo_year, file_date_taken, full_file_path)


def get_date_taken(full_file_path):

    metadata = pyexiv2.ImageMetadata(full_file_path)
    metadata.read()

    file_date_taken = metadata['Exif.Image.DateTime'].raw_value if 'Exif.Image.DateTime' in metadata.exif_keys else None

    if not file_date_taken or "0000:00:00" in file_date_taken:
        return None

    return datetime.datetime.strptime(file_date_taken, '%Y:%m:%d %H:%M:%S')


def set_date_taken(full_file_path, date_taken):

    print "Updating date taken"
    metadata = pyexiv2.ImageMetadata(full_file_path)
    metadata.read()
    metadata['Exif.Image.DateTime'] = date_taken.strftime('%Y:%m:%d %H:%M:%S')
    metadata.write()


def fill_empty_date_taken_exif_with_estimate(full_file_path):
    photo_year = get_elder_year_directory(full_file_path)

    if not photo_year:
        return

    meta = pyexiv2.ImageMetadata(full_file_path)
    meta.read()

    file_date_taken = meta['Exif.Image.DateTime'].raw_value if 'Exif.Image.DateTime' in meta.exif_keys else None

    if file_date_taken and "0000:00:00" not in file_date_taken:
        return

    date_created = get_creation_time(full_file_path)

    #if it seems reasonable, let's use file creation date, otherwise, just set the year based on the elder folder
    if photo_year == date_created:
        set_date_taken(full_file_path, date_created)
    else:
        set_date_taken(full_file_path, datetime.datetime(year=photo_year, month=1, day=1))


root_directory = "/Users/reustmd/Google Drive/Photos"
#print_date_taken_exif_contradicts_elder_year_folder
file_cleanup_strategies = [ensure_lower_case_file_name, fill_empty_date_taken_exif_with_estimate]

for directory_path, _, file_names in os.walk(root_directory):
    photo_file_names = [file_name for file_name in file_names if is_photo_file(file_name)]

    for file_name in photo_file_names:
        absolute_path = os.path.abspath(os.path.join(directory_path, file_name))

        for strategy in file_cleanup_strategies:
            strategy(absolute_path)