project('komikku',
    version: '0.8.0',
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

# NOTE: if you contributed, feel free to add your name and email address here
contributors = '\n'.join([
    'Valéry Febvre (valos) &lt;vfebvre@easter-eggs.com&gt;',
])
translators = '\n'.join([
    'Valéry Febvre (valos) &lt;vfebvre@easter-eggs.com&gt; (French)',
    'VaGNaroK &lt;indialuz42@gmail.com&gt; (Brazilian Portuguese)',
])

python = import('python3')

prefix = get_option('prefix') # should be /usr
profile = get_option('profile') # should be default or development
bindir = get_option('bindir') # should be /bin
datadir = get_option('datadir') # should be /usr/share
pkgdatadir = join_paths(prefix, datadir, meson.project_name())
pythondir = join_paths(prefix, python.sysconfig_path('purelib'))
localedir = join_paths(prefix, get_option('localedir'))

app_id = '.'.join([domainext, domainname, prettyname])
app_id_aspath = '/'.join([domainext, domainname, prettyname])

install_subdir(meson.project_name(), install_dir: pythondir)

subdir('data')
subdir('bin')
subdir('po')

meson.add_install_script('meson_post_install.py')
