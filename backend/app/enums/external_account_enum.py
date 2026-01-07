from enum import Enum


class EXTERNAL_ACCOUNT_PROVIDER(str, Enum):
    GOOGLE_DRIVE = "google_drive"
    CANVAS = "canvas"
    CHATGPT = "chatgpt"
    ONE_DRIVE = "one_drive"
    NOTION = "notion"
    DROPBOX = "dropbox"
