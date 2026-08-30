var desktops = desktopsForActivity(currentActivity());
for (var i = 0; i < desktops.length; ++i) {
    desktops[i].wallpaperPlugin = "org.kde.image";
    desktops[i].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    desktops[i].writeConfig("Image", "file:///usr/share/backgrounds/quantic/quantic-wallpaper.svg");
}
var panel = new Panel;
panel.location = "bottom";
panel.height = 54;
panel.floating = true;
panel.alignment = "center";
panel.addWidget("org.kde.plasma.kickoff");
panel.addWidget("org.kde.plasma.icontasks");
panel.addWidget("org.kde.plasma.marginsseparator");
panel.addWidget("org.kde.plasma.systemtray");
panel.addWidget("org.kde.plasma.digitalclock");
