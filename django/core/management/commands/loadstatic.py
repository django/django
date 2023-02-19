from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import fileinput
import glob, os
import shutil
import re

class Command(BaseCommand):
    help = 'load all url for static img,js,css'
    pattern_executed = []

    def prepend_line(self, path, line):
        with open(path, 'r') as old:
            os.unlink(path)
            with open(path, 'w') as new:
                new.write(str(line) + "\n")
                shutil.copyfileobj(old, new)

    def replace_in_file(self, file_path, search_text, new_text):
        with fileinput.input(file_path, inplace=True) as file:
            for line in file:
                new_line = line.replace(search_text, new_text)
                print(new_line, end='')

    def checkfile_replace_need(self, file, lines):
        result_replace = False

        for line in lines:
            result_replace = self.check_pattern(line, file, just_check=True)
            if result_replace == True:
                return result_replace
        return result_replace

    def check_pattern(self, html, file_path="", just_check=False):
        replace_need = False
        is_image = re.findall(r'<img.*?src=["|\'](.*?)["|\']', html, re.I)
        is_javascript = re.findall(r'<script[^<>]+src=["\']([^"\'<>]+\.js)["\']', html, re.I)
        is_css = re.findall(r'<link[^<>]+href=["\']([^"\'<>]+\.(?:css|png))["\']', html, re.I)
        all_replace = is_image + is_javascript + is_css
        file_paths = "".join(file_path.split(str(settings.TEMPLATES[0]['DIRS'][0])))

        if len(all_replace) >= 1:
            for replace in all_replace:
                if "{%" not in replace and replace not in self.pattern_executed:
                    search = replace
                    replace_string = " ".join(["{% static", '"{}"'.format(replace), '%}'])
                    replace_need = True
                    if not just_check:
                        print("replace {} to \"{}\" file {}".format(search, replace_string, file_paths))
                        self.replace_in_file(file_path, search, replace_string)
                        self.pattern_executed.append(search)

        if replace_need:
            return True
        else:
            return False

    def handle(self, *args, **options):

        for file in glob.glob(str(settings.TEMPLATES[0]['DIRS'][0])+"/*.html"):
            fs = open(file, "r")
            lines = [line.strip() for line in fs.readlines()]

            file_path = "".join(file.split(str(settings.TEMPLATES[0]['DIRS'][0])))

            if "{% load static %}" not in lines:
                # print("no detect load_static")
                self.stdout.write(self.style.ERROR('no detect : load_static variable inside template {}'.format(file_path)))
                self.prepend_line(file, "{% load static %}")

            check_replace = self.checkfile_replace_need(file, lines)

            if check_replace == True:
                lineinput = input("do you want to automaticaly for file {} replace assets path ? [Y/n]\n".format(file_path))

                if "n" in lineinput or "N" in lineinput:
                    continue

                if "y" in lineinput or "Y" in lineinput:
                    # write first line

                    for line in lines:
                        result_replace = self.check_pattern(line, file)
