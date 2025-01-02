from .CombineAudioVideoAndUpload import CombineAudioVideoAndUpload, VideoAudioLoader, LoadAudioURL, CombineAudio

NODE_CLASS_MAPPINGS = {
    "CombineAudioVideoAndUpload": CombineAudioVideoAndUpload,
    "VideoAudioLoader": VideoAudioLoader,
    "LoadAudioURL": LoadAudioURL,
    "CombineAudio": CombineAudio
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineAudioVideoAndUpload": "Combine Audio and Video, Upload to Drive",
    "VideoAudioLoader": "Load Video/Audio from URL or Upload",
    "LoadAudioURL": "Load Audio from URL",
    "CombineAudio": "Combine Two Audios (Music offsets w.r.t Voice)"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
