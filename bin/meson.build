# Profiles
conf = configuration_data()

conf.set_quoted('PROFILE', profile)
conf.set('VERSION', meson.project_version())
conf.set('PYTHON', py_installation.path())
conf.set('prefix', prefix)
conf.set('datadir', datadir)
conf.set('pkgdatadir', pkgdatadir)
conf.set('pythondir', join_paths(prefix, pythondir))
conf.set('localedir', join_paths(prefix, localedir))
conf.set('projectname', meson.project_name())
conf.set('prettyname', prettyname)
conf.set('authorfullname', authorfullname)
conf.set('authoremail', authoremail)
conf.set('appid', app_id)

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
