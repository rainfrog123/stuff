import json

class LocationConfig:
    """
    Configuration for location settings.

    Attributes:
        location (str): Website requests your current location. Default is "ask".
                        - "ask": Ask for permission (default setting, same as common browsers)
                        - "allow": Always allow website to obtain your location information
                        - "block": Always block obtaining location
        location_switch (str): 1 for location generated based on IP (default), 0 for custom location.
                        - "1": Location generated based on IP (default setting)
                        - "0": Custom location
        longitude (float): Longitude of the location, from -180 to 180. Default is None.
        latitude (float): Latitude of the location, from -90 to 90. Default is None.
        accuracy (int): Distance of location accuracy, from 10 to 5000 meters. Default is 1000.
    """
    def __init__(self, location="ask", location_switch="1", longitude=None, latitude=None, accuracy=1000):
        self.location = location
        self.location_switch = location_switch
        self.longitude = longitude
        self.latitude = latitude
        self.accuracy = accuracy

    def to_dict(self):
        return {
            "location": self.location,
            "location_switch": self.location_switch,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "accuracy": self.accuracy
        }

class LanguageConfig:
    """
    Configuration for language settings.

    Attributes:
        language (list): Browser languages. Default is ["en-US", "en"].
        language_switch (str): Configure languages based on IP country. Default is "1".
                        - "1": On (default)
                        - "0": Off
        page_language_switch (str): Match interface language based on [language]. Default is "1".
                        - "1": Enabled (default)
                        - "0": Disabled
        page_language (str): Page language. Default is "native".
                        - "native": The local language (default)
                        - "en-US": Example to specify the language code
    """
    def __init__(self, language=None, language_switch="1", page_language_switch="1", page_language="native"):
        self.language = language or ["en-US", "en"]
        self.language_switch = language_switch
        self.page_language_switch = page_language_switch
        self.page_language = page_language

    def to_dict(self):
        return {
            "language": self.language,
            "language_switch": self.language_switch,
            "page_language_switch": self.page_language_switch,
            "page_language": self.page_language
        }

class WebGLConfig:
    """
    Configuration for WebGL settings.

    Attributes:
        unmasked_vendor (str): The unmasked vendor. Default is "".
        unmasked_renderer (str): The unmasked renderer. Default is "".
        webgpu (dict): WebGPU settings. Default is {"webgpu_switch": "1"}.
    """
    def __init__(self, unmasked_vendor="", unmasked_renderer="", webgpu=None):
        self.unmasked_vendor = unmasked_vendor
        self.unmasked_renderer = unmasked_renderer
        self.webgpu = webgpu or {"webgpu_switch": "1"}

    def to_dict(self):
        return {
            "unmasked_vendor": self.unmasked_vendor,
            "unmasked_renderer": self.unmasked_renderer,
            "webgpu": self.webgpu
        }

class RandomUA:
    """
    Configuration for random User-Agent settings.

    Attributes:
        ua_browser (list): List of browsers. Default is ["chrome"].
        ua_version (list): List of versions. Default is ["80"].
        ua_system_version (list): List of system versions. Default is ["Windows 10"].

    Supported System Versions:
        - Android (Specify version: Android 9, Android 10, Android 11, Android 12, Android 13)
        - iOS (Specify version: iOS 14, iOS 15)
        - Windows (Specify version: Windows 7, Windows 8, Windows 10, Windows 11)
        - Mac OS X (Specify version: Mac OS X 10, Mac OS X 11, Mac OS X 12, Mac OS X 13)
        - Linux
    """
    def __init__(self, ua_browser=None, ua_version=None, ua_system_version=None):
        self.ua_browser = ua_browser or ["chrome"]
        self.ua_version = ua_version or ["126"]
        self.ua_system_version = ua_system_version or [""]

    def to_dict(self):
        return {
            "ua_browser": self.ua_browser,
            "ua_version": self.ua_version,
            "ua_system_version": self.ua_system_version
        }

class MediaDevicesNum:
    """
    Configuration for media devices settings.

    Attributes:
        audioinput_num (str): Number of microphones. Default is "1".
        videoinput_num (str): Number of cameras. Default is "1".
        audiooutput_num (str): Number of speakers. Default is "1".
    """
    def __init__(self, audioinput_num="1", videoinput_num="1", audiooutput_num="1"):
        self.audioinput_num = audioinput_num
        self.videoinput_num = videoinput_num
        self.audiooutput_num = audiooutput_num

    def to_dict(self):
        return {
            "audioinput_num": self.audioinput_num,
            "videoinput_num": self.videoinput_num,
            "audiooutput_num": self.audiooutput_num
        }

class MacAddressConfig:
    """
    Configuration for MAC address settings.

    Attributes:
        model (str): Model for MAC address. Default is "1".
                        - "0": Use the MAC address of the current computer.
                        - "1": Match an appropriate value instead of the real MAC address (default).
                        - "2": Custom appropriate value instead of the real MAC address.
        address (str): Custom MAC address if model is "2". Default is "".
    """
    def __init__(self, model="1", address=""):
        self.model = model
        self.address = address

    def to_dict(self):
        return {
            "model": self.model,
            "address": self.address
        }

class BrowserKernelConfig:
    """
    Configuration for browser kernel settings.

    Attributes:
        version (str): Browser kernel version. Default is "ua_auto".
                        - "ua_auto": Smart match kernel version (default)
                        - "92": 92 version of the kernel
                        - "99": 99 version of the kernel
        type (str): Browser type. Default is "chrome".
                        - "chrome": Use Chrome browser (default)
                        - "firefox": Use Firefox browser
    """
    def __init__(self, version="ua_auto", type="chrome"):
        self.version = version
        self.type = type

    def to_dict(self):
        return {
            "version": self.version,
            "type": self.type
        }

class FingerprintConfig:
    """
    Main configuration for fingerprint settings.

    Attributes:
        automatic_timezone (str): Timezone generation. Default is "1".
                        - "1": Timezone automatically generated based on IP (default)
                        - "0": Custom timezone
        timezone (str): Custom timezone. Default is "".
        webrtc (str): WebRTC settings. Default is "disabled".
                        - "disabled": Disabled (default)
                        - "proxy": Replace (use proxy IP to cover real IP)
                        - "local": Real (the local IP is acquired)
                        - "forward": Use proxy IP to cover real IP, high-security
        ua (str): User-agent string. Default is None.
        screen_resolution (str): Screen resolution. Default is "none".
                        - "none": Follow current computer (default)
                        - "random": Random resolution
                        - "width_height": Custom resolution separated by "_"
        fonts (list): Browser fonts. Default is ["all"].
                        - "all": Use all available fonts (default)
        canvas (str): Canvas fingerprint switch. Default is "1".
                        - "1": Add noise (default)
                        - "0": Use the current computer default Canvas
        webgl_image (str): WebGL image fingerprint switch. Default is "1".
                        - "1": Add noise (default)
                        - "0": Use the current computer default WebGL
        webgl (str): WebGL metadata fingerprint switch. Default is "3".
                        - "3": Random matching (default)
                        - "0": Computer default
                        - "2": Custom (need to define webgl_config)
        audio (str): Audio fingerprint switch. Default is "1".
                        - "1": Add noise (default)
                        - "0": Close
        do_not_track (str): DNT configuration switch. Default is "default".
                        - "default": Default
                        - "true": Open
                        - "false": Close
        hardware_concurrency (str): Number of CPU cores. Default is "4".
                        - "4": Default value if parameter is not passed
                        - "2": Two cores
                        - "6": Six cores
                        - "8": Eight cores
                        - "16": Sixteen cores
        device_memory (str): Device memory. Default is "8".
                        - "8": Default value if parameter is not passed
                        - "2": 2 GB
                        - "4": 4 GB
                        - "6": 6 GB
        flash (str): Flash configuration switch. Default is "block".
                        - "block": Block (default)
                        - "allow": Allow
        scan_port_type (str): Port scan protection. Default is "1".
                        - "1": Enable (default)
                        - "0": Close
        allow_scan_ports (list): Ports allowed to be scanned. Default is [].
        client_rects (str): ClientRects configuration. Default is "1".
                        - "1": Add noise (default)
                        - "0": Use the default ClientRects of the current computer
        speech_switch (str): SpeechVoices configuration. Default is "1".
                        - "1": Use a value to replace the real SpeechVoices (default)
                        - "0": Each profile uses the default SpeechVoices of the current computer
        gpu (str): GPU settings. Default is "0".
                        - "0": Deploy settings from [Local settings - Hardware acceleration] (default)
                        - "1": Turn on hardware acceleration
                        - "2": Turn off hardware acceleration
    """
    def __init__(self,
                 automatic_timezone="1",
                 timezone="",
                 webrtc="disabled",
                 ua=None,
                 screen_resolution="none",
                 fonts=None,
                 canvas="1",
                 webgl="3",
                 webgl_config=None,
                 audio="1",
                 do_not_track="default",
                 hardware_concurrency="4",
                 device_memory="8",
                 flash="block",
                 scan_port_type="1",
                 allow_scan_ports=None,
                 client_rects="1",
                 speech_switch="1",
                 gpu="0",
                 location_config=None,
                 language_config=None,
                 media_devices_num=None,
                 random_ua=None,
                 mac_address_config=None,
                 browser_kernel_config=None):
        
        self.automatic_timezone = automatic_timezone
        self.timezone = timezone
        self.webrtc = webrtc
        self.ua = ua
        self.screen_resolution = screen_resolution
        self.fonts = fonts or ["all"]
        self.canvas = canvas
        self.webgl = webgl
        self.webgl_config = webgl_config or WebGLConfig()
        self.audio = audio
        self.do_not_track = do_not_track
        self.hardware_concurrency = hardware_concurrency
        self.device_memory = device_memory
        self.flash = flash
        self.scan_port_type = scan_port_type
        self.allow_scan_ports = allow_scan_ports or []
        self.client_rects = client_rects
        self.speech_switch = speech_switch
        self.gpu = gpu
        self.location_config = location_config or LocationConfig()
        self.language_config = language_config or LanguageConfig()
        self.media_devices_num = media_devices_num or MediaDevicesNum()
        self.random_ua = random_ua or RandomUA()
        self.mac_address_config = mac_address_config or MacAddressConfig()
        self.browser_kernel_config = browser_kernel_config or BrowserKernelConfig()

    def to_dict(self):
        return {
            "automatic_timezone": self.automatic_timezone,
            "timezone": self.timezone,
            "webrtc": self.webrtc,
            "ua": self.ua,
            "screen_resolution": self.screen_resolution,
            "fonts": self.fonts,
            "canvas": self.canvas,
            "webgl": self.webgl,
            "webgl_config": self.webgl_config.to_dict(),
            "audio": self.audio,
            "do_not_track": self.do_not_track,
            "hardware_concurrency": self.hardware_concurrency,
            "device_memory": self.device_memory,
            "flash": self.flash,
            "scan_port_type": self.scan_port_type,
            "allow_scan_ports": self.allow_scan_ports,
            "client_rects": self.client_rects,
            "speech_switch": self.speech_switch,
            "gpu": self.gpu,
            "location_config": self.location_config.to_dict(),
            "language_config": self.language_config.to_dict(),
            "media_devices_num": self.media_devices_num.to_dict(),
            "random_ua": self.random_ua.to_dict(),
            "mac_address_config": self.mac_address_config.to_dict(),
            "browser_kernel_config": self.browser_kernel_config.to_dict()
        }

# Example usage
fingerprint_config = FingerprintConfig(
    # location_config=LocationConfig(longitude=-40.123321, latitude=30.123321)
)

print(json.dumps(fingerprint_config.to_dict(), indent=4))
