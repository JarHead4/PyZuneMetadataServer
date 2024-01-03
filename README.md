# PyZuneMetadataServer
A recreation of the Microsoft CD metadata servers in Python.

These services (windowsmedia.com for WMP 7-9, toc.music.metaservices.microsoft.com and images.metaservices.microsoft.com for WMP 10+ and Zune) were shut down some time in 2019, leaving Zune clients and Windows Media Player clients not on Windows 10 unable to automatically get metadata for inserted CDs.

This project aims to recreate these services, so you can now automatically view and rip CDs to your library with metadata from MusicBrainz.

Windows Media Player 7+ and all versions of the Zune software are confirmed to work.

To connect to the public version, add the following entries to HOSTS:

```
135.181.88.32        toc.music.metaservices.microsoft.com
135.181.88.32        info.music.metaservices.microsoft.com
135.181.88.32        images.metaservices.microsoft.com
135.181.88.32        redir.metaservices.microsoft.com
135.181.88.32        windowsmedia.com
```
