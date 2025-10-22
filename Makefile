install:
	ln -s $$(pwd) ~/.local/share/ulauncher/extensions

enable:
	systemctl --user enable ulauncher --now

disable:
	systemctl --user disable ulauncher --now
