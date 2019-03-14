## Update pot files from source files
```
cd po

intltool-update --maintain

cd ..

find mangascan -iname "*.py" | xargs xgettext --language=Python --keyword=_ --output=po/mangascan-python.pot

find data -iname "*.ui" | xargs xgettext --output=po/mangascan-glade.pot -L Glade

msgcat --to-code=UTF-8 --use-first po/mangascan-glade.pot po/mangascan-python.pot > po/mangascan.pot

rm po/mangascan-glade.pot po/mangascan-python.pot
```

## Generate po file for language
```
cd po

msginit --locale=xx --input=mangascan.pot
```

## Update language po file
```
cd po

msgmerge -N xx.po mangascan.pot
```

## Compile po file
```
msgfmt --output-file=xx.mo xx.po
```
