datadir = join_paths('share', 'icons')
icondir = join_paths('hicolor', 'scalable', 'apps')
if get_option('profile') == 'development'
install_data (
    join_paths(icondir, 'com.gitlab.valos.MangaScan.svg'),
    install_dir: join_paths(datadir, icondir),
    rename: 'com.gitlab.valos.MangaScanDevel.svg'
)
else
install_data (
    join_paths(icondir, 'com.gitlab.valos.MangaScan.svg'),
    install_dir: join_paths(datadir, icondir)
)
endif

icondir = join_paths('hicolor', 'symbolic', 'apps')
if get_option('profile') == 'development'
install_data (
    join_paths(icondir, 'com.gitlab.valos.MangaScan-symbolic.svg'),
    install_dir: join_paths(datadir, icondir),
    rename: 'com.gitlab.valos.MangaScanDevel-symbolic.svg'
)
else
install_data (
    join_paths(icondir, 'com.gitlab.valos.MangaScan-symbolic.svg'),
    install_dir: join_paths(datadir, icondir)
)
endif
