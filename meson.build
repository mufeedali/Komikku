project('komikku',
    version: '0.24.0',
    meson_version: '>= 0.50.0',
    license: 'GPL3'
)

description = 'An online/offline manga reader'
prettyname = 'Komikku'
prettylicense = 'GPL-3.0+'

authornickname = 'valos'
authorfullname = 'Valéry Febvre'
authoremail = 'vfebvre@easter-eggs.com'

# app_id built as: domainext.domainname.prettyname
domainname = 'febvre'
domainext = 'info'

gitrepo = 'https://gitlab.com/' + authornickname + '/' + prettyname
website = gitrepo

python = import('python')
py_installation = python.find_installation('python3')
if not py_installation.found()
    error('No valid python3 binary found')
else
    message('Found python3 binary')
endif

prefix = get_option('prefix') # should be /usr
profile = get_option('profile') # should be default or development
bindir = get_option('bindir') # should be /bin
datadir = get_option('datadir') # should be /usr/share
pkgdatadir = join_paths(prefix, datadir, meson.project_name())
pythondir = py_installation.get_install_dir()
localedir = join_paths(prefix, get_option('localedir'))

app_id = '.'.join([domainext, domainname, prettyname])
app_id_aspath = '/'.join([domainext, domainname, prettyname])

install_subdir(meson.project_name(), install_dir: pythondir)

subdir('data')
subdir('bin')
subdir('po')

meson.add_install_script('meson_post_install.py')
