i18n = import('i18n')
gnome = import('gnome')

#
# .desktop file
#
desktop_conf = configuration_data()
desktop_conf.set('bindir', join_paths(prefix, bindir))
desktop_conf.set('prettyname', prettyname)
# .desktop comment now hardcoded for better i18n support
#desktop_conf.set('description', description)
desktop_conf.set('appid', app_id)
desktop_conf.set('projectname', meson.project_name())

desktop_file = configure_file(
    input: app_id + '.desktop.in',
    output: app_id + '.desktop.i18n.in',
    #install: true,
    #install_dir: join_paths(datadir, 'applications'),
    configuration: desktop_conf
)

# Merges translations
i18n.merge_file(
    input: desktop_file,
    output: app_id + '.desktop',
    po_dir: '../po',
    type: 'desktop',
    install: true,
    install_dir: join_paths(datadir, 'applications')
)

# Validating the .desktop file
desktop_file_validate = find_program('desktop-file-validate', required:false)
if desktop_file_validate.found()
test (
    'Validate desktop file',
    desktop_file_validate,
    args: join_paths(meson.current_build_dir (), app_id + '.desktop')
)
endif

#
# Dependencies
#
python_bin = python.find_python()
if not python_bin.found()
    error('No valid python3 binary found')
else
    message('Found python3 binary')
endif
dependency('glib-2.0')
dependency('gobject-introspection-1.0', version: '>=1.35.9')
dependency('gtk+-3.0', version :'>=3.20')
dependency('libhandy-1', version :'>=0.90.0')

#
# gschema XML file
#
gschema_conf = configuration_data()
gschema_conf.set('apppath', app_id_aspath)
gschema_conf.set('appid', app_id)
gschema_conf.set('projectname', meson.project_name())

configure_file(
    input: app_id + '.gschema.xml.in',
    output: app_id + '.gschema.xml',
    configuration: gschema_conf,
    install: true,
    install_dir: join_paths(datadir, 'glib-2.0/schemas'),
)

# Validating schemas
compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
    test('Validate schema file', compile_schemas,
        args: ['--strict', '--dry-run', meson.current_source_dir()]
    )
endif

subdir('ui')
subdir('icons')

#
# gresource XML file
#
message('Compile gresource XML file')
app_resources = gnome.compile_resources(app_id,
    app_id + '.gresource.xml',
    gresource_bundle: true,
    dependencies: configure_file(
        input: 'ui/about_dialog.ui.in',
        output: 'about_dialog.ui',
        configuration: glade_conf
    ),
    install: true,
    install_dir: pkgdatadir
)

#
# appdata XML file
#
message('Merge translations of appdata XML file')
i18n.merge_file(
    input: app_id + '.appdata.xml.in',
    output: app_id + '.appdata.xml',
    po_dir: '../po',
    install: true,
    install_dir: join_paths(datadir, 'metainfo')
)

appstreamcli = find_program('appstream-util', required: false)
if appstreamcli.found()
    test (
        'Validate appdata file',
        appstreamcli,
        args: ['validate-relax', join_paths(meson.current_build_dir (), app_id + '.appdata.xml')]
    )
endif
