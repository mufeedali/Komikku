#!/bin/bash

version=$(fgrep "version: " ../meson.build | grep -v "meson" | grep -o "'.*'" | sed "s/'//g")

find ../komikku -iname "*.py" | xargs xgettext --package-name=Komikku --package-version=$version --from-code=UTF-8 --output=komikku-python.pot
find ../data/ui -iname "*.ui" -or -iname "*.xml" -or -iname "*.ui.in" | xargs xgettext --package-name=Komikku --package-version=$version --from-code=UTF-8 --output=komikku-glade.pot -L Glade
find ../data/ -iname "*.desktop.in" | xargs xgettext --package-name=Komikku --package-version=$version --from-code=UTF-8 --output=komikku-desktop.pot -L Desktop
find ../data/ -iname "*.appdata.xml.in" | xargs xgettext --no-wrap --package-name=Komikku --package-version=$version --from-code=UTF-8 --output=komikku-appdata.pot

msgcat --use-first komikku-python.pot komikku-glade.pot komikku-desktop.pot komikku-appdata.pot > komikku.pot

sed 's/#: //g;s/:[0-9]*//g;s/\.\.\///g' <(fgrep "#: " komikku.pot) | sed s/\ /\\n/ | sort | uniq > POTFILES.in

echo "# Please keep this list alphabetically sorted" > LINGUAS
for l in $(ls *.po); do basename $l .po >> LINGUAS; done

for lang in $(sed "s/^#.*$//g" LINGUAS); do
    mv "${lang}.po" "${lang}.po.old"
    msginit --locale=$lang --input komikku.pot
    mv "${lang}.po" "${lang}.po.new"
    msgmerge -N "${lang}.po.old" "${lang}.po.new" > ${lang}.po
    rm "${lang}.po.old" "${lang}.po.new"
done

rm komikku-*.pot

# To create language file use this command
# msginit --locale=LOCALE --input komikku.pot
# where LOCALE is something like `de`, `it`, `es`...

# To compile a .po file
# msgfmt --output-file=xx.mo xx.po
# where xx is something like `de`, `it`, `es`...
