dev-install:
	ln -s $$(pwd) ~/.local/share/ulauncher/extensions

restart:
	systemctl --user restart ulauncher

enable:
	systemctl --user enable ulauncher --now

disable:
	systemctl --user disable ulauncher --now
