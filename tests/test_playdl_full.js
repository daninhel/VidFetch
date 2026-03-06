const play = require('play-dl');

async function test() {
    try {
        const info = await play.video_info('https://www.youtube.com/watch?v=MMV94bm_Vpc');
        const format18 = info.format.find(f => f.itag === 18);
        console.log("format 18 full object: ", JSON.stringify(format18, null, 2));

        const format140 = info.format.find(f => f.itag === 140);
        console.log("format 140 full object: ", JSON.stringify(format140, null, 2));
    } catch(err) {
        console.error("Error: ", err);
    }
}
test();
