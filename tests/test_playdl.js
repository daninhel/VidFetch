const play = require('play-dl');

async function test() {
    try {
        const info = await play.video_info('https://www.youtube.com/watch?v=MMV94bm_Vpc');
        console.log("Keys: ", Object.keys(info.format[0]));
        for(let i=0; i<3; i++) {
           let f = info.format[i];
           console.log(`itag: ${f.itag}, mimeType: ${f.mimeType}, hasVideo: ${f.hasVideo}, hasAudio: ${f.hasAudio}, url: ${f.url ? 'Yes' : 'No'}`);
        }
    } catch(err) {
        console.error("Error: ", err);
    }
}
test();
