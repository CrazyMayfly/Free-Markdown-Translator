import datetime, exifread
import os


class Helper:
    def __init__(self, basedir):
        self.basedir = basedir
        # new_exif = exifread.Exif()
        # new_exif['Image Artist'] = 'John Doe'
        # new_exif['Image Copyright'] = 'Copyright © 2023 John Doe'

    @staticmethod
    def get_formatted_cur_time():
        now = datetime.datetime.now()
        offset = datetime.timezone(datetime.timedelta(hours=8))
        formatted_time = now.replace(microsecond=0).astimezone(offset).isoformat()
        print(formatted_time)

    def get_img_names(self):
        images = []
        for path, dir_list, file_list in os.walk(self.basedir):
            for filename in file_list:
                splitext = os.path.splitext(filename)
                prefix = splitext[0]
                suffix = splitext[-1]
                if suffix != '.md':
                    realpath = os.path.join(path, filename)
                    image = {"realpath": realpath, "prefix": prefix, "suffix": suffix}
                    images.append(image)
            return images

    def rename_images(self):
        index = 1
        for image in self.get_img_names():
            prefix = image['prefix']
            if prefix.isdigit() and int(prefix) >= index:
                index = int(prefix) + 1

        for image in self.get_img_names():
            realpath = image['realpath']
            prefix = image['prefix']
            suffix = image['suffix']
            if prefix != 'cover' and not prefix.isdigit():
                os.rename(realpath, os.path.join(self.basedir, str(index) + suffix))
                index += 1

    def add_copyrights(self):
        images = self.get_img_names()
        for image in self.get_img_names():
            realpath = image['realpath']
            prefix = image['prefix']
            suffix = image['suffix']
            # Open image file for reading (binary mode)
            f = open(realpath, 'rb')

            # Return Exif tags
            tags = exifread.process_file(f)
            for tag in tags.keys():
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
                    print("Key: %s, value %s" % (tag, tags[tag]))
            break


if __name__ == '__main__':
    helper = Helper("C:\\Users\\admin\Desktop\Blog\content\post\五一")
    helper.get_formatted_cur_time()
    # helper.rename_images()
