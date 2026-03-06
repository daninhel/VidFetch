const play = require('play-dl');

async function test() {
    try {
        const stream = await play.stream('https://www.youtube.com/watch?v=MMV94bm_Vpc', { quality: 18 });
        console.log("Stream keys: ", Object.keys(stream));
        console.log("Stream type: ", stream.type);
    } catch(err) {
        console.error("Error: ", err);
    }
}
test();
