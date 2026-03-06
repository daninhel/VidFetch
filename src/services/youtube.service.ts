import youtubedl from 'youtube-dl-exec';
import { sanitizeFilename } from '../utils/validation.util';

export class YouTubeService {
    constructor() { }

    public async getVideoFormats(url: string) {
        // Obter iformações em formato JSON bruto via yt-dlp (youtube-dl-exec)
        const info = await youtubedl(url, {
            dumpSingleJson: true,
            noCheckCertificates: true,
            noWarnings: true,
            youtubeSkipDashManifest: true, // Ignorar manifestos DASH as vezes quebra itag especificos, mas otimiza velocidade. Melhor setar falso ou não enviar.
        }) as any;

        const cleanTitle = sanitizeFilename(info.title || 'Video');

        const mp4Streams: any[] = [];
        const webmStreams: any[] = [];
        const mp3Streams: any[] = [];
        const m4aStreams: any[] = [];

        const seenMp4 = new Set();
        const seenWebm = new Set();
        const seenMp3 = new Set();
        const seenM4a = new Set();

        info.formats.forEach((f: any) => {
            const hasAudio = f.acodec !== 'none';
            const hasVideo = f.vcodec !== 'none';
            const isProgressive = hasAudio && hasVideo;
            const ext = (f.ext || '').toLowerCase();
            const itag = parseInt(f.format_id, 10);

            // Video Formats
            if (hasVideo) {
                // Em yt-dlp a qualidade geralmente está explícita no height ou format_note
                const resolution = f.height ? `${f.height}p` : f.format_note;
                if (!resolution) return;

                if (ext === 'mp4' && !seenMp4.has(resolution)) {
                    seenMp4.add(resolution);
                    mp4Streams.push({
                        itag,
                        quality: resolution,
                        type: 'video',
                        progressive: isProgressive,
                        needs_merge: !isProgressive,
                        available: true
                    });
                }
                else if (ext === 'webm' && !seenWebm.has(resolution)) {
                    seenWebm.add(resolution);
                    webmStreams.push({
                        itag,
                        quality: resolution,
                        type: 'video',
                        progressive: isProgressive,
                        needs_merge: !isProgressive,
                        available: true
                    });
                }
            }

            // Audio Formats
            if (hasAudio && !hasVideo) {
                const abr = f.abr ? `${Math.round(f.abr)}kbps` : 'unknown';

                if (ext === 'm4a' || ext === 'mp4') {
                    if (!seenM4a.has(abr)) {
                        seenM4a.add(abr);
                        m4aStreams.push({
                            itag,
                            quality: abr,
                            type: 'audio',
                            mime: `audio/${ext}`,
                            progressive: false,
                            needs_merge: false,
                            available: true
                        });
                    }
                }
                else if (ext === 'webm') {
                    if (!seenMp3.has(abr)) {
                        seenMp3.add(abr);
                        mp3Streams.push({
                            itag,
                            quality: abr,
                            type: 'audio',
                            mime: `audio/webm`,
                            progressive: false,
                            needs_merge: false,
                            available: true
                        });
                    }
                }
            }
        });

        const sortByQuality = (a: any, b: any) => parseInt(b.quality) - parseInt(a.quality);
        mp4Streams.sort(sortByQuality);
        webmStreams.sort(sortByQuality);
        mp3Streams.sort(sortByQuality);
        m4aStreams.sort(sortByQuality);

        return {
            title: info.title,
            thumbnail: info.thumbnail || '',
            author: info.uploader || 'YouTube',
            duration: info.duration || 0,
            ffmpeg: false,
            safe_title: cleanTitle,
            formats: {
                mp4: mp4Streams,
                webm: webmStreams,
                mp3: mp3Streams,
                m4a: m4aStreams
            }
        };
    }

    public async getStreamInfoByItag(url: string, itag: number) {
        const formatInfo = await youtubedl(url, {
            dumpSingleJson: true,
            format: itag.toString(),
            noCheckCertificates: true,
            noWarnings: true
        }) as any;

        if (!formatInfo || !formatInfo.url) {
            throw new Error(`Format with itag ${itag} not found for this video or could not be decrypted.`);
        }

        const cleanTitle = sanitizeFilename(formatInfo.title || 'Video');

        return {
            info: formatInfo,
            format: formatInfo,
            cleanTitle,
            directUrl: formatInfo.url,
            hasAudio: formatInfo.acodec !== 'none',
            hasVideo: formatInfo.vcodec !== 'none',
            mimeType: formatInfo.ext ? `video/${formatInfo.ext}` : 'video/mp4'
        };
    }
}
