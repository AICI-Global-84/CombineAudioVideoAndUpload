import torchaudio
import folder_paths
import requests
import io
import os
import tempfile
import hashlib
import numpy as np
import soundfile as sf
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_audioclips, AudioClip
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json

class CombineAudioVideoAndUpload:
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    SERVICE_ACCOUNT_FILE = '/content/drive/My Drive/SD-Data/comfyui-n8n-aici01-7679b55c962b.json'
    DRIVE_FOLDER_ID = '1fZyeDT_eW6ozYXhqi_qLVy-Xnu5JD67a'

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video": ("VIDEO",),
                "audio": ("AUDIO",),
                "start_duration": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1,
                    "display": "number"
                }),
                "end_duration": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1,
                    "display": "number"
                })
            }
        }

    RETURN_TYPES = ("STRING", "VIDEO",)
    RETURN_NAMES = ("file_url", "combined_video",)
    FUNCTION = "combine_and_upload"
    CATEGORY = "video/audio"

    def __init__(self):
        self.drive_service = None
        self._initialize_drive_service()

    def _initialize_drive_service(self):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.SERVICE_ACCOUNT_FILE, scopes=self.SCOPES)
            self.drive_service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error initializing Drive service: {str(e)}")
            raise RuntimeError(f"Failed to initialize Drive service: {str(e)}")
            
    def _upload_to_drive(self, file_path):
        try:
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [self.DRIVE_FOLDER_ID]
            }
            media = MediaFileUpload(file_path, resumable=True)
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            self.drive_service.permissions().create(
                fileId=file.get('id'),
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()

            file_id = file.get('id')
            return f"https://drive.google.com/uc?id={file_id}"

        except Exception as e:
            raise RuntimeError(f"Failed to upload to Drive: {str(e)}")

    def combine_and_upload(self, video, audio, start_duration, end_duration):
        """
        Kết hợp video và audio, sau đó upload lên Drive.
        """
        temp_output_path = None  # Khởi tạo biến temp_output_path để tránh lỗi UnboundLocalError
    
        try:
            # Debug: In loại dữ liệu và giá trị của video và audio
            print(f"Video input type: {type(video)}")
            print(f"Audio input type: {type(audio)}")
            print(f"Video input: {video}")
            print(f"Audio input: {audio}")
    
            # Lưu video byte vào file tạm thời nếu video là dạng byte
            if isinstance(video, bytes):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video_file:
                    temp_video_file.write(video)
                    temp_video_path = temp_video_file.name
                    video_clip = VideoFileClip(temp_video_path)
            else:
                raise TypeError(f"Invalid video input: {video}")
    
            # Nếu audio là dạng tensor, lưu nó ra file .wav
            if isinstance(audio, dict) and 'waveform' in audio and 'sample_rate' in audio:
                waveform = audio['waveform'].numpy()  # Chuyển tensor thành numpy array
                waveform = waveform.squeeze()  # Loại bỏ chiều không cần thiết
                sample_rate = audio['sample_rate']
    
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio_file:
                    sf.write(temp_audio_file.name, waveform, sample_rate)  # Lưu audio ra file wav
                    temp_audio_path = temp_audio_file.name
    
                audio_clip = AudioFileClip(temp_audio_path)
            else:
                raise TypeError(f"Invalid audio input: {audio}")
    
            # Xử lý phần còn lại như bình thường
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
                temp_output_path = temp_output.name
    
                # Tính tổng độ dài của video cần tạo
                total_duration = start_duration + audio_clip.duration + end_duration
    
                # Cắt video sao cho khớp với tổng độ dài cần có
                if video_clip.duration < total_duration:
                    video_clip = video_clip.loop(duration=total_duration)
                else:
                    video_clip = video_clip.subclip(0, total_duration)
    
                # Tạo đoạn audio silent trước khi audio chính bắt đầu
                silent_audio = AudioClip(lambda t: 0, duration=start_duration, fps=audio_clip.fps)
                
                # Nối đoạn silent với đoạn audio thực
                final_audio_clip = concatenate_audioclips([silent_audio, audio_clip])
    
                # Kết hợp video và audio
                final_clip = CompositeVideoClip([video_clip])
                final_clip = final_clip.set_audio(final_audio_clip)  # Gán âm thanh cho video
    
                # Lưu video đầu ra với audio
                final_clip.write_videofile(
                    temp_output_path,
                    codec='libx264',
                    audio_codec='aac',  # Đảm bảo sử dụng codec âm thanh đúng
                    remove_temp=True
                )
    
                drive_url = self._upload_to_drive(temp_output_path)
    
                video_clip.close()
                audio_clip.close()
                final_clip.close()
    
                with open(temp_output_path, 'rb') as f:
                    combined_video = {'path': temp_output_path, 'data': f.read()}
    
                return (drive_url, combined_video)
    
        except Exception as e:
            raise RuntimeError(f"Failed to combine video and audio: {str(e)}")
    
        finally:
            # Kiểm tra nếu temp_output_path đã được khởi tạo và xóa file tạm
            if temp_output_path and os.path.exists(temp_output_path):
                os.unlink(temp_output_path)


class VideoAudioLoader:
    """
    Node để tải video từ URL

    Class methods
    -------------
    INPUT_TYPES (dict):
        Định nghĩa các tham số đầu vào cho node.

    Attributes
    ----------
    RETURN_TYPES (`tuple`):
        Kiểu dữ liệu cho mỗi phần tử trong tuple đầu ra.
    RETURN_NAMES (`tuple`):
        Tên tùy chọn cho mỗi đầu ra trong tuple đầu ra.
    FUNCTION (`str`):
        Tên phương thức entry-point. Ví dụ, nếu `FUNCTION = "load"`, thì nó sẽ chạy VideoAudioLoader().load()
    OUTPUT_NODE ([`bool`]):
        Nếu node này là một output node để xuất kết quả từ đồ thị.
    CATEGORY (`str`):
        Danh mục mà node nên xuất hiện trong giao diện.
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_url": ("STRING", {
                    "multiline": False,
                    "default": "http://example.com/video.mp4",
                    "lazy": True
                }),
            },
        }

    RETURN_TYPES = ("VIDEO",)  # Kiểu đầu ra là VIDEO
    FUNCTION = "load"          # Tên phương thức entry-point
    CATEGORY = "Media Loader"   # Danh mục cho node

    def load(self, video_url):
        # Logic tải video từ URL
        video_data = self.download_file(video_url)
        return (video_data,)  # Trả về video đã tải

    def download_file(self, url):
        # Logic để tải file từ URL
        import requests
        response = requests.get(url)
        return response.content  # Trả về nội dung của video
        

class LoadAudioURL:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"audio_url": ("STRING", {"default": "https://example.com/audio.flac"})}}

    CATEGORY = "audio"

    RETURN_TYPES = ("AUDIO", )
    FUNCTION = "load_from_url"

    def load_from_url(self, audio_url):
        # Download the audio file from the URL
        response = requests.get(audio_url)
        if response.status_code != 200:
            raise Exception(f"Failed to download audio from URL: {audio_url}")

        # Load the audio from the downloaded content
        audio_file = io.BytesIO(response.content)
        waveform, sample_rate = torchaudio.load(audio_file)
        audio = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
        return (audio, )

    @classmethod
    def IS_CHANGED(s, audio_url):
        m = hashlib.sha256()
        m.update(audio_url.encode('utf-8'))
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(s, audio_url):
        try:
            response = requests.head(audio_url)
            if response.status_code != 200:
                return f"Invalid audio URL: {audio_url}"
        except Exception as e:
            return f"Error accessing audio URL: {str(e)}"
        return True


class CombineAudio:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "voice": ("AUDIO", ),
                "music": ("AUDIO", ),
                "voice_volume": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1,
                    "display": "number"
                }),
                "music_volume": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1,
                    "display": "number"
                }),
                "start_duration": ("FLOAT", {
                    "default": 0.0,
                    "min": -60.0,
                    "max": 60.0,
                    "step": 0.1,
                    "display": "number"
                }),
                "end_duration": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 60.0,
                    "step": 0.1,
                    "display": "number"
                }),
            }
        }

    RETURN_TYPES = ("AUDIO", )
    FUNCTION = "combine"
    CATEGORY = "audio"

    def combine(self, 
                voice, 
                music, 
                voice_volume, 
                music_volume, 
                start_duration, 
                end_duration):
        """
        ...
        """
        try:
            voice_waveform = voice["waveform"].squeeze(0)
            sr_voice = voice["sample_rate"]

            music_waveform = music["waveform"].squeeze(0)
            sr_music = music["sample_rate"]

            # Thay vì raise, ta resample
            if sr_voice != sr_music:
                target_sr = max(sr_voice, sr_music)
                if sr_voice != target_sr:
                    transform = torchaudio.transforms.Resample(sr_voice, target_sr)
                    voice_waveform = transform(voice_waveform.unsqueeze(0)).squeeze(0)
                    sr_voice = target_sr
                if sr_music != target_sr:
                    transform = torchaudio.transforms.Resample(sr_music, target_sr)
                    music_waveform = transform(music_waveform.unsqueeze(0)).squeeze(0)
                    sr_music = target_sr

            sr = sr_voice

            # Đưa mọi thứ về mono để xử lý đơn giản (nếu muốn giữ stereo, cần code phức tạp hơn)
            if voice_waveform.ndim > 1:
                voice_waveform = voice_waveform.mean(dim=0)
            if music_waveform.ndim > 1:
                music_waveform = music_waveform.mean(dim=0)

            # Tính độ dài (giây) của voice và music
            voice_len = voice_waveform.shape[-1] / sr
            music_len = music_waveform.shape[-1] / sr

            # Voice luôn bắt đầu ở t=0 trong final mix
            # => ta xét music_start = start_duration (có thể âm, dương, hoặc 0)
            music_start = start_duration    # giây
            music_end   = voice_len + end_duration  # music kết thúc muộn hơn voice end_duration giây

            # 1) Tính subclip của music (theo timeline final):
            #    - Nếu music_start < 0, ta bỏ qua phần ban đầu của music (-music_start giây)
            #    - Nếu music_end > music_len, music cũng chỉ có tối đa music_len
            # 
            # => ta muốn music chạy trong đoạn [music_start, music_end] (theo timeline final)
            #    map ngược về music waveform gốc => [0, music_len]
            # 
            # => Subclip music: 
            #    start_in_music = -music_start (nếu music_start < 0), 
            #                     0 nếu music_start >= 0
            #    end_in_music   = start_in_music + (music_end - music_start)
            # 
            #    nhưng phải cắt tối đa = music_len

            # Tính start_in_music (giây) và end_in_music (giây)
            if music_start < 0:
                start_in_music = -music_start
            else:
                start_in_music = 0.0

            desired_duration = music_end - music_start  # khoảng thời gian ta muốn có music
            if desired_duration <= 0:
                # end < start => voice quá dài, hoặc end_duration < -start_duration ...
                # => music không kịp phát, ta trả về voice mà không có music
                return self._return_mono_audio(voice_waveform * voice_volume, sr)

            end_in_music = start_in_music + desired_duration

            # Giới hạn subclip không vượt quá music_len
            end_in_music = min(end_in_music, music_len)

            if start_in_music >= music_len or end_in_music <= 0:
                # Trường hợp music không còn gì để phát
                # => Chỉ có voice
                return self._return_mono_audio(voice_waveform * voice_volume, sr)

            # Convert to sample
            start_sample = int(start_in_music * sr)
            end_sample   = int(end_in_music * sr)

            # Subclip waveform của music
            music_subclip = music_waveform[start_sample:end_sample]

            # Tính offset của music_subclip trong final mix
            # music_start >= 0 => music vào trễ => offset = music_start
            # music_start < 0  => voice vào trễ => offset = 0 (vì voice ở 0), 
            #                     music_subclip thực ra đã bị cắt bớt phần đầu
            if music_start < 0:
                music_offset_in_final = 0  # music khởi đầu ngay tại voice = 0 (nhưng thực ra cắt bớt
            else:
                music_offset_in_final = int(music_start * sr)

            # Tính độ dài voice (samples)
            voice_len_samples = voice_waveform.shape[-1]

            # Tính độ dài final mix
            # voice_end = voice_len_samples
            # music_end_in_final = music_offset_in_final + music_subclip.shape[-1]
            # Nhưng ta cũng cần xem music_end (giây) so với voice_len
            final_len_samples = max(
                voice_len_samples,  # voice
                music_offset_in_final + music_subclip.shape[-1]  # music
            )

            # Khởi tạo final mix mono
            final_mix = np.zeros(final_len_samples, dtype=np.float32)

            # Thêm voice vào final mix (volume)
            voice_np = voice_waveform.numpy() * voice_volume
            final_mix[:voice_len_samples] += voice_np[:final_len_samples]

            # Thêm music subclip vào final mix (volume)
            music_np = music_subclip.numpy() * music_volume

            end_index = music_offset_in_final + music_np.shape[-1]
            if end_index > final_len_samples:
                end_index = final_len_samples

            final_mix[music_offset_in_final:end_index] += music_np[:(end_index - music_offset_in_final)]

            # Chuyển final_mix -> tensor
            final_torch = torchaudio.functional.to_tensor(final_mix).unsqueeze(0)

            # Trả về AUDIO format cho ComfyUI
            return ({
                "waveform": final_torch,
                "sample_rate": sr
            }, )

        except Exception as e:
            raise RuntimeError(f"Lỗi khi trộn audio: {str(e)}")

    def _return_mono_audio(self, np_audio_mono, sr):
        """
        Tiện ích để trả về một AUDIO dictionary dạng mono
        """
        if not isinstance(np_audio_mono, np.ndarray):
            np_audio_mono = np_audio_mono.numpy()

        if np_audio_mono.ndim == 1:
            # shape [samples]
            final_torch = torchaudio.functional.to_tensor(np_audio_mono).unsqueeze(0)
        else:
            # shape [samples, ...] -> ép về [samples]
            final_torch = torchaudio.functional.to_tensor(np_audio_mono.squeeze()).unsqueeze(0)

        return ({
            "waveform": final_torch,
            "sample_rate": sr
        }, )

        except Exception as e:
            raise RuntimeError(f"Lỗi khi trộn audio: {str(e)}")


    @classmethod
    def IS_CHANGED(s, 
                   voice, 
                   music, 
                   voice_volume, 
                   music_volume, 
                   start_duration, 
                   end_duration):
        """
        Hàm băm đầu vào để xác định node có thay đổi gì không (ComfyUI dùng để cache).
        """
        m = hashlib.sha256()
        # Băm một số đặc tính
        m.update(str(voice["sample_rate"]).encode('utf-8'))
        m.update(str(voice["waveform"].shape).encode('utf-8'))
        m.update(str(music["sample_rate"]).encode('utf-8'))
        m.update(str(music["waveform"].shape).encode('utf-8'))
        m.update(str(voice_volume).encode('utf-8'))
        m.update(str(music_volume).encode('utf-8'))
        m.update(str(start_duration).encode('utf-8'))
        m.update(str(end_duration).encode('utf-8'))
        return m.digest().hex()

            
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
