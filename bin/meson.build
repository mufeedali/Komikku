# Profiles
if get_option('profile') == 'development'
    profile = 'Devel'
    name_suffix = ' (Development)'
else
    profile = ''
    name_suffix = ''
endif

conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set_quoted('PROFILE', profile)
conf.set('pkgdatadir', pkgdatadir)
conf.set('PYTHON', python.find_python().path())
conf.set('pythondir', join_paths(prefix, pythondir))
conf.set('localedir', join_paths(prefix, localedir))
conf.set('projectname', meson.project_name())
conf.set('authorfullname', authorfullname)
conf.set('authoremail', authoremail)
conf.set('appid', '.'.join([domainext, domainname, prettyname]))

configure_file(
  input: meson.project_name() + '.in',
  output: meson.project_name(),
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

myprogram = join_paths(meson.build_root(), 'bin', meson.project_name())
run_target('run',
  command: [myprogram]
)
