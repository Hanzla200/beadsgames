[app]

title = 12 Beads
package.name = twelvebeads
package.domain = com.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
requirements = python3,kivy,android,pyjnius,https://github.com/MichaelStott/KivMob/archive/refs/heads/master.zip
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 36
android.minapi = 23
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
android.gradle_dependencies = com.google.android.gms:play-services-ads:23.6.0
android.enable_androidx = True
android.meta_data = com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-3940256099942544~3347511713

[buildozer]
log_level = 2
warn_on_root = 1
