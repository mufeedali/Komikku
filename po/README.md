## Update POTFILES.in

Search for left out files, which must been listed in POTFILES.in

```
cd po

intltool-update --maintain
```

Check missing and notexist files and update POTFILES.in

## Generate po file for new language
```
cd po

msginit --locale=xx --input=mangascan.pot
```

## Update pot file (template)
```
xgettext -f POTFILES.in -o mangascan.pot
```

## Update language po file
```
cd po

msgmerge --update -N --backup=none xx.po mangascan.pot
```

## Translate po file
```
poedit xx.po
```

## Compile po file
```
msgfmt --output-file=xx.mo xx.po
```
