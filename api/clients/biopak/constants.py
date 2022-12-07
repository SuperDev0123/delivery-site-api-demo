from django.conf import settings

if settings.ENV == "local":
    CSV_DIR = "/Users/admin/work/goldmine/scripts/dir01/"
    ARCHIVE_CSV_DIR = "/Users/admin/work/goldmine/scripts/dir02/"
else:

    CSV_DIR = "/home/cope_au/dme_sftp/startrack_au/pickup_ext/indata/"
    ARCHIVE_CSV_DIR = "/home/cope_au/dme_sftp/startrack_au/pickup_ext/archive/"

FTP_INFO = {
    "name": "BIOPAK",
    "host": "ftp.biopak.com.au",
    "username": "dme_biopak",
    "password": "3rp2NcHS",
    "sftp_filepath": "/DME/POD/",
    "local_filepath": CSV_DIR,
    "local_filepath_archive": ARCHIVE_CSV_DIR,
}
