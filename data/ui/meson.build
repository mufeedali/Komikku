glade_conf = configuration_data()

glade_conf.set('APPID', app_id)
glade_conf.set('PACKAGE_URL', website)
glade_conf.set('DATA_DIR', pkgdatadir)

# This is for development version
#glade_conf.set('VERSION', ''.join([run_command(['git', 'describe', '--long', '--tags']).stdout(), get_option('profile')]))
glade_conf.set('VERSION', meson.project_version())

glade_conf.set('CONTRIBUTORS', contributors)
glade_conf.set('authorfullname', authorfullname)
glade_conf.set('authoremail', authoremail)
glade_conf.set('prettyname', prettyname)
