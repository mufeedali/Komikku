message('Install icons')

# Scalable
icondir = join_paths(datadir, 'icons/hicolor/scalable/apps')
if get_option('profile') == 'development'
install_data (
    'info.febvre.MangaScan.svg',
    install_dir: icondir,
    rename: 'info.febvre.MangaScanDevel.svg'
)
else
install_data (
    'info.febvre.MangaScan.svg',
    install_dir: icondir
)
endif

# Symbolic
icondir = join_paths(datadir, 'icons/hicolor/symbolic/apps')
if get_option('profile') == 'development'
install_data (
    'info.febvre.MangaScan-symbolic.svg',
    install_dir: icondir,
    rename: 'info.febvre.MangaScanDevel-symbolic.svg'
)
else
install_data (
    'info.febvre.MangaScan-symbolic.svg',
    install_dir: icondir
)
endif
