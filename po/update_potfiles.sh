#!/bin/bash

rm *.pot

version=$(fgrep "version: " ../meson.build | grep -v "meson" | grep -o "'.*'" | sed "s/'//g")

find ../mangascan -iname "*.py" | xargs xgettext --package-name=MangaScan --package-version=$version --from-code=UTF-8 --output=mangascan-python.pot
find ../data/ui -iname "*.ui" -or -iname "*.xml" | xargs xgettext --package-name=MangaScan --package-version=$version --from-code=UTF-8 --output=mangascan-glade.pot -L Glade
find ../data/ -iname "*.desktop.in" | xargs xgettext --package-name=MangaScan --package-version=$version --from-code=UTF-8 --output=mangascan-desktop.pot -L Desktop
find ../data/ -iname "*.appdata.xml.in" | xargs xgettext --no-wrap --package-name=MangaScan --package-version=$version --from-code=UTF-8 --output=mangascan-appdata.pot

msgcat --use-first mangascan-python.pot mangascan-glade.pot mangascan-desktop.pot mangascan-appdata.pot > mangascan.pot

sed 's/#: //g;s/:[0-9]*//g;s/\.\.\///g' <(fgrep "#: " mangascan.pot) | sed s/\ /\\n/ | sort | uniq > POTFILES.in

echo "# Please keep this list alphabetically sorted" > LINGUAS
for l in $(ls *.po); do basename $l .po >> LINGUAS; done

for lang in $(sed "s/^#.*$//g" LINGUAS); do
    mv "${lang}.po" "${lang}.po.old"
    msginit --locale=$lang --input mangascan.pot
    mv "${lang}.po" "${lang}.po.new"
    msgmerge -N "${lang}.po.old" "${lang}.po.new" > ${lang}.po
    rm "${lang}.po.old" "${lang}.po.new"
done

rm *.pot

# To create language file use this command
# msginit --locale=LOCALE --input mangascan.pot
# where LOCALE is something like `de`, `it`, `es`...

# To compile a .po file
# msgfmt --output-file=xx.mo xx.po
# where xx is something like `de`, `it`, `es`...
