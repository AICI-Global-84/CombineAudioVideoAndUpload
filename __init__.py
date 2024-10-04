from .CombineAudioVideoAndUpload import CombineAudioVideoAndUpload, VideoAudioLoader

NODE_CLASS_MAPPINGS = {
    "CombineAudioVideoAndUpload": CombineAudioVideoAndUpload,
    "VideoAudioLoader": VideoAudioLoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineAudioVideoAndUpload": "Combine Audio and Video, Upload to Drive",
    "VideoAudioLoader": "Load Video/Audio from URL or Upload"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
