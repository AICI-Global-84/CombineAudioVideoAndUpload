from .CombineAudioVideoAndUpload import CombineAudioVideoAndUpload, VideoAudioLoader, LoadAudioURL

NODE_CLASS_MAPPINGS = {
    "CombineAudioVideoAndUpload": CombineAudioVideoAndUpload,
    "VideoAudioLoader": VideoAudioLoader,
    "LoadAudioURL": LoadAudioURL
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineAudioVideoAndUpload": "Combine Audio and Video, Upload to Drive",
    "VideoAudioLoader": "Load Video/Audio from URL or Upload",
    "LoadAudioURL": "Load Audio from URL"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
