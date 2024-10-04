import os
import moviepy.editor as mp
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

class CombineAudioVideoAndUpload:
    def __init__(self):
        self.drive_service = self.authenticate_google_drive()

    def authenticate_google_drive(self):
        """Authenticate and create a Google Drive API service."""
        SCOPES = ['https://www.googleapis.com/auth/drive']
        credentials_path = '/content/drive/My Drive/SD-Data/comfyui-n8n-aici01-7679b55c962b.json'  # Đường dẫn đến credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES)
        return build('drive', 'v3', credentials=credentials)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("FILE", {"tooltip": "The input video file."}),
                "audio": ("FILE", {"tooltip": "The input audio file."}),
                "start_duration": ("FLOAT", {"default": 0, "tooltip": "The time (in seconds) the video starts before audio."}),
                "end_duration": ("FLOAT", {"default": 0, "tooltip": "The time (in seconds) the video ends after audio."})
            }
        }

    RETURN_TYPES = ("STRING", "FILE")
    RETURN_NAMES = ("file_url", "combined_video")
    FUNCTION = "combine_and_upload"
    OUTPUT_NODE = True
    CATEGORY = "video"

    def combine_video_audio(self, video_path, audio_path, start_duration, end_duration, output_path):
        """Combine video and audio, adjusting durations as specified."""
        video = mp.VideoFileClip(video_path)
        audio = mp.AudioFileClip(audio_path)

        # Adjust video length based on audio and duration settings
        adjusted_start = max(0, start_duration)
        adjusted_end = video.duration - (audio.duration + adjusted_start) + end_duration

        if adjusted_end < 0:
            adjusted_end = 0  # Avoid negative trimming

        # Set audio to video and save
        combined = video.subclip(adjusted_start, video.duration - adjusted_end).set_audio(audio)
        combined.write_videofile(output_path, codec="libx264", audio_codec="aac")

    def upload_to_google_drive(self, file_path):
        """Upload the combined video to Google Drive and return the shareable URL."""
        try:
            file_metadata = {'name': os.path.basename(file_path), 'parents': ['1fZyeDT_eW6ozYXhqi_qLVy-Xnu5JD67a']}  # ID thư mục cụ thể
            media = MediaFileUpload(file_path, mimetype='video/mp4')
            file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            # Get file ID and create a shareable link
            file_id = file.get('id')
            self.drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
            return f"https://drive.google.com/uc?id={file_id}"
        except Exception as e:
            print(f"An error occurred while uploading to Google Drive: {e}")
            return None

    def combine_and_upload(self, video, audio, start_duration=0, end_duration=0):
        output_file = "/tmp/combined_output.mp4"  # Tạo file tạm thời

        # Combine video and audio
        self.combine_video_audio(video, audio, start_duration, end_duration, output_file)

        # Upload to Google Drive and get public URL
        public_file_url = self.upload_to_google_drive(output_file)
        if not public_file_url:
            return ("", output_file)

        return (public_file_url, output_file)


# A dictionary that contains all nodes you want to export with their names
NODE_CLASS_MAPPINGS = {
    "CombineAudioVideoAndUpload": CombineAudioVideoAndUpload
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "CombineAudioVideoAndUpload": "Combine Audio and Video, Upload to Drive"
}
