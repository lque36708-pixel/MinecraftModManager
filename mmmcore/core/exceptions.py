class MMMError(Exception):
    pass

class ProfileNotFoundError(MMMError):
    def __init__(self, path=None):
        msg = "No profile set in this directory."
        if path:
            msg += f" ({path})"
        msg += "\nMake sure you are in your Minecraft mods folder, then set a profile."
        super().__init__(msg)

class ModNotFoundError(MMMError):
    def __init__(self, name):
        super().__init__(f"No mod found matching '{name}'")

class APIConnectionError(MMMError):
    def __init__(self, reason):
        super().__init__(f"Connection failed: {reason}")

class APIError(MMMError):
    def __init__(self, code, reason):
        self.code = code
        self.reason = reason
        super().__init__(f"API error {code}: {reason}")

class ValidationError(MMMError):
    pass

class DownloadError(MMMError):
    def __init__(self, msg):
        super().__init__(f"Download failed: {msg}")

class ChecksumError(MMMError):
    def __init__(self):
        super().__init__("Checksum mismatch! File may be corrupted.")
