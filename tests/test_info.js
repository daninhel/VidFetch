require('ts-node').register();
const { YouTubeService } = require('./src/services/youtube.service.ts');

async function run() {
    const s = new YouTubeService();
    try {
        console.log("Fetching formats via YouTubeService...");
        const formats = await s.getVideoFormats('https://www.youtube.com/watch?v=MMV94bm_Vpc');
        console.log("Success! Extracted formats:", formats.formats.mp4.length);
    } catch(e) {
        console.error("ERROR in YouTubeService:", e);
    }
}
run();
